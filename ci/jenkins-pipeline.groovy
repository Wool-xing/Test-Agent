/**
 * Jenkins Pipeline - 自动化测试流水线
 * 支持：冒烟 / 回归 / 全量 + JMeter 性能阶段（双模式）
 * 质量门禁统一调用 utils/ci_quality_gate.py 与 utils/jmeter_result_parser.py
 */
pipeline {
    agent {
        docker {
            // python:3.11（非 slim），含 wget/tar/字体等系统依赖；--with-deps 仍会用 apt 装额外组件
            image 'python:3.11'
            args  '-v /tmp:/tmp --network=host'
        }
    }

    parameters {
        choice(
            name: 'TEST_LEVEL',
            choices: ['smoke', 'regression', 'full'],
            description: '测试级别：smoke=P0 冒烟, regression=P0+P1 回归, full=全量'
        )
        choice(
            name: 'TEST_ENV',
            choices: ['test', 'staging'],
            description: '测试环境'
        )
        choice(
            name: 'PERF_MODE',
            choices: ['ci_quick', 'full'],
            description: 'JMeter 性能模式：ci_quick=5 并发/1 分钟, full=50 并发/5 分钟'
        )
        booleanParam(
            name: 'NOTIFY_ON_SUCCESS',
            defaultValue: true,
            description: '成功时是否发送通知'
        )
    }

    environment {
        // 从 Jenkins Credentials 读取（均为 Secret text）
        TEST_APP_URL      = credentials('TEST_APP_URL')
        TEST_API_URL      = credentials('TEST_API_URL')
        TEST_DB_HOST      = credentials('TEST_DB_HOST')
        TEST_DB_PASSWORD  = credentials('TEST_DB_PASSWORD')
        TEST_USER         = credentials('TEST_USER')
        TEST_PASS         = credentials('TEST_PASS')
        ADMIN_USER        = credentials('ADMIN_USER')
        ADMIN_PASS        = credentials('ADMIN_PASS')
        PERF_TEST_USER    = credentials('PERF_TEST_USER')
        PERF_TEST_PASS    = credentials('PERF_TEST_PASS')
        ZENTAO_BASE_URL   = credentials('ZENTAO_BASE_URL')
        ZENTAO_ACCOUNT    = credentials('ZENTAO_ACCOUNT')
        ZENTAO_PASSWORD   = credentials('ZENTAO_PASSWORD')

        // 工作目录
        WORKSPACE_DIR     = "${WORKSPACE}/workspace"
        ALLURE_DIR        = "${WORKSPACE_DIR}/执行日志/allure-results"
        SCREENSHOT_DIR    = "${WORKSPACE_DIR}/执行日志/截图"
        APP_SRC_PATH      = "./src"
        JMETER_VERSION    = "5.6.3"
        HEADLESS          = 'true'
    }

    options {
        timeout(time: 4, unit: 'HOURS')
        timestamps()
        ansiColor('xterm')
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '5'))
    }

    stages {
        // ===== 准备 =====
        stage('准备') {
            options { timeout(time: 15, unit: 'MINUTES') }
            steps {
                script {
                    echo "=========================================="
                    echo " 测试级别: ${params.TEST_LEVEL}"
                    echo " 测试环境: ${params.TEST_ENV}"
                    echo " 性能模式: ${params.PERF_MODE}"
                    echo " 构建号:   ${BUILD_NUMBER}"
                    echo "=========================================="
                }
                // mkdir 拆开（不依赖 bash brace expansion）
                sh '''
                    set -e
                    pip install -r requirements.txt --quiet
                    playwright install chromium --with-deps
                    mkdir -p workspace/执行日志/allure-results
                    mkdir -p workspace/执行日志/截图
                    mkdir -p workspace/执行日志/jmeter-results
                    mkdir -p workspace/执行日志/jmeter-report
                    mkdir -p workspace/执行日志/coverage-report
                    mkdir -p workspace/执行日志/baselines
                    mkdir -p workspace/执行日志/history
                    mkdir -p workspace/测试报告
                    mkdir -p workspace/测试用例
                    mkdir -p workspace/测试数据
                    mkdir -p workspace/自动化脚本/python/pages
                    mkdir -p workspace/自动化脚本/python/api
                    mkdir -p workspace/自动化脚本/python/tests
                    mkdir -p workspace/自动化脚本/python/scripts
                    mkdir -p workspace/自动化脚本/jmeter
                    mkdir -p workspace/需求分析
                '''
            }
        }

        // ===== 冒烟测试 =====
        stage('冒烟测试（P0）') {
            options { timeout(time: 15, unit: 'MINUTES') }
            steps {
                sh '''
                    set -e
                    pytest -m "p0" \
                        -n 2 \
                        --timeout=60 \
                        --tb=short \
                        --alluredir="${ALLURE_DIR}" \
                        --junitxml="${WORKSPACE_DIR}/执行日志/smoke-results.xml" \
                        -v 2>&1 | tee workspace/执行日志/smoke.log
                '''
            }
            post {
                always {
                    junit "${WORKSPACE_DIR}/执行日志/smoke-results.xml"
                    sh '''
                        python -m utils.ci_quality_gate \
                            --smoke-xml "${WORKSPACE_DIR}/执行日志/smoke-results.xml" \
                            --output-json "${WORKSPACE_DIR}/执行日志/smoke_gate_result.json"
                    '''
                    script {
                        env.STAGE_SMOKE_OK = 'true'
                    }
                }
                failure {
                    script {
                        env.STAGE_SMOKE_OK = 'false'
                    }
                }
            }
        }

        // ===== 回归测试（marker 化筛选） =====
        stage('回归测试') {
            when { expression { return params.TEST_LEVEL in ['regression', 'full'] && env.STAGE_SMOKE_OK == 'true' } }
            options { timeout(time: 90, unit: 'MINUTES') }
            parallel {
                stage('API 回归') {
                    steps {
                        sh '''
                            set -e
                            pytest -m "(p0 or p1) and api" \
                                -n 4 \
                                --reruns=2 --reruns-delay=5 \
                                --timeout=120 \
                                --cov="${APP_SRC_PATH}" \
                                --cov-report=xml:workspace/执行日志/coverage-api.xml \
                                --alluredir="${ALLURE_DIR}" \
                                --junitxml="${WORKSPACE_DIR}/执行日志/api-results.xml" \
                                -v 2>&1 | tee workspace/执行日志/api.log
                        '''
                    }
                }
                stage('UI 回归') {
                    steps {
                        sh '''
                            set -e
                            pytest -m "(p0 or p1) and ui" \
                                -n 2 \
                                --reruns=2 --reruns-delay=5 \
                                --timeout=180 \
                                --cov="${APP_SRC_PATH}" \
                                --cov-report=xml:workspace/执行日志/coverage-ui.xml \
                                --alluredir="${ALLURE_DIR}" \
                                --junitxml="${WORKSPACE_DIR}/执行日志/ui-results.xml" \
                                -v 2>&1 | tee workspace/执行日志/ui.log
                        '''
                    }
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'workspace/执行日志/api-results.xml,workspace/执行日志/ui-results.xml'
                    script {
                        env.STAGE_REGRESSION_OK = (currentBuild.currentResult == 'SUCCESS') ? 'true' : 'false'
                    }
                }
            }
        }

        // ===== JMeter 性能测试 =====
        stage('性能测试（JMeter）') {
            when { expression { return params.TEST_LEVEL in ['regression', 'full'] && env.STAGE_REGRESSION_OK == 'true' } }
            options { timeout(time: 30, unit: 'MINUTES') }
            steps {
                // 1) 安装 JMeter（含 archive 兜底） + withEnv 持久 PATH
                script {
                    def jmeterHome = "/opt/apache-jmeter-${env.JMETER_VERSION}"
                    sh """
                        set -e
                        if [ ! -x "${jmeterHome}/bin/jmeter" ]; then
                            if ! wget -q "https://downloads.apache.org/jmeter/binaries/apache-jmeter-${env.JMETER_VERSION}.tgz" -O /tmp/jmeter.tgz; then
                                wget -q "https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-${env.JMETER_VERSION}.tgz" -O /tmp/jmeter.tgz
                            fi
                            tar -xzf /tmp/jmeter.tgz -C /opt/
                        fi
                        ${jmeterHome}/bin/jmeter --version
                    """
                    withEnv(["PATH+JMETER=${jmeterHome}/bin"]) {
                        // 2) 生成 CSV
                        sh '''
                            set -e
                            if [ "$PERF_MODE" = "full" ]; then COUNT=50; else COUNT=10; fi
                            python -m utils.jmeter_csv_exporter --count "$COUNT" \
                                --output workspace/测试数据/jmeter_users.csv
                        '''

                        // 3) 解析 TEST_API_URL → host/protocol/port
                        sh '''
                            set -e
                            python - <<EOF
import os, urllib.parse
url = os.environ.get("TEST_API_URL", "")
p = urllib.parse.urlparse(url)
host = p.hostname or ""
proto = p.scheme or "http"
port = str(p.port or (443 if proto == "https" else 80))
with open("workspace/.target_meta.env", "w") as f:
    f.write(f"TARGET_HOST={host}\\n")
    f.write(f"TARGET_PROTOCOL={proto}\\n")
    f.write(f"TARGET_PORT={port}\\n")
EOF
                        '''

                        // 4) 执行 JMeter
                        sh '''
                            set -e
                            . workspace/.target_meta.env

                            if [ "$PERF_MODE" = "full" ]; then
                                THREADS=50; RAMPUP=60; DURATION=300
                            else
                                THREADS=5;  RAMPUP=10; DURATION=60
                            fi

                            jmeter -n \
                                -t workspace/自动化脚本/jmeter/test_plan.jmx \
                                -l "${WORKSPACE_DIR}/执行日志/jmeter-results/result.jtl" \
                                -e -o "${WORKSPACE_DIR}/执行日志/jmeter-report/" \
                                -Jtarget_host="${TARGET_HOST}" \
                                -Jtarget_protocol="${TARGET_PROTOCOL}" \
                                -Jtarget_port="${TARGET_PORT}" \
                                -Jthreads=${THREADS} -Jrampup=${RAMPUP} -Jduration=${DURATION} \
                                -j "${WORKSPACE_DIR}/执行日志/jmeter-results/jmeter.log" \
                                2>&1 | tee workspace/执行日志/jmeter.log
                        '''

                        // 5) 解析 + 性能门禁（基线对比，仅 full+release+PASS 才更新）
                        sh '''
                            set -e
                            UPDATE_FLAG=""
                            if [ "$PERF_MODE" = "full" ] && echo "$BRANCH_NAME" | grep -q "^release/"; then
                                UPDATE_FLAG="--update-baseline"
                            fi
                            python -m utils.jmeter_result_parser \
                                "${WORKSPACE_DIR}/执行日志/jmeter-results/result.jtl" \
                                --mode "${PERF_MODE}" \
                                --baseline "${WORKSPACE_DIR}/执行日志/baselines/perf_baseline.json" \
                                --regression-max-pct 20 \
                                ${UPDATE_FLAG}
                        '''
                    }
                }
            }
            post {
                always {
                    archiveArtifacts(
                        artifacts: 'workspace/执行日志/jmeter-results/**,workspace/执行日志/jmeter-report/**,workspace/执行日志/baselines/**',
                        allowEmptyArchive: true
                    )
                }
                failure {
                    script {
                        env.STAGE_PERF_OK = 'false'
                        if (env.WECHAT_WEBHOOK) {
                            sh """
                                curl -s -X POST "${WECHAT_WEBHOOK}" \
                                  -H 'Content-Type: application/json' \
                                  -d '{"msgtype":"markdown","markdown":{"content":"⚠️ **性能测试未达标** | 构建#${BUILD_NUMBER} | 模式:${PERF_MODE} | [查看报告](${BUILD_URL}artifact/workspace/执行日志/jmeter-report/index.html)"}}'
                            """
                        }
                    }
                }
                success {
                    script { env.STAGE_PERF_OK = 'true' }
                }
            }
        }

        // ===== 全量覆盖率 =====
        stage('全量覆盖率') {
            when { expression { return params.TEST_LEVEL == 'full' } }
            options { timeout(time: 60, unit: 'MINUTES') }
            steps {
                sh '''
                    set -e
                    pytest \
                        --cov="${APP_SRC_PATH}" \
                        --cov-report=xml:workspace/执行日志/coverage.xml \
                        --cov-report=html:workspace/执行日志/coverage-report \
                        --cov-fail-under=80 \
                        --timeout=300 \
                        -q
                '''
                publishHTML(target: [
                    reportDir:       'workspace/执行日志/coverage-report',
                    reportFiles:     'index.html',
                    reportName:      '代码覆盖率报告',
                    keepAll:         true,
                    alwaysLinkToLastBuild: true
                ])
            }
        }

        // ===== Allure 报告 =====
        stage('测试报告') {
            steps {
                allure([
                    includeProperties: true,
                    jdk: 'JDK17',  // 配置 Jenkins → Tools → JDK，不可为空字符串
                    properties: [],
                    reportBuildPolicy: 'ALWAYS',
                    results: [[path: "${ALLURE_DIR}"]]
                ])
            }
        }
    }

    post {
        always {
            // 多扩展名拆开（Jenkins ant pattern 不支持 brace expansion）
            archiveArtifacts(
                artifacts: 'workspace/执行日志/**/*.xml,workspace/执行日志/**/*.log,workspace/执行日志/**/*.png,workspace/执行日志/**/*.json',
                allowEmptyArchive: true
            )
        }

        success {
            script {
                if (params.NOTIFY_ON_SUCCESS && env.WECHAT_WEBHOOK) {
                    sh """
                        curl -s -X POST "${WECHAT_WEBHOOK}" \
                          -H 'Content-Type: application/json' \
                          -d '{"msgtype":"markdown","markdown":{"content":"✅ **测试通过** | 构建#${BUILD_NUMBER} | 级别:${TEST_LEVEL} | 模式:${PERF_MODE} | [查看报告](${BUILD_URL}allure/)"}}'
                    """
                }
            }
        }

        failure {
            script {
                if (env.WECHAT_WEBHOOK) {
                    sh """
                        curl -s -X POST "${WECHAT_WEBHOOK}" \
                          -H 'Content-Type: application/json' \
                          -d '{"msgtype":"markdown","markdown":{"content":"❌ **测试失败** | 构建#${BUILD_NUMBER} | 级别:${TEST_LEVEL} | [查看报告](${BUILD_URL}allure/)"}}'
                    """
                }
            }
        }

        cleanup {
            sh '''
                find workspace/测试数据 -name "*.json" -mtime +7 -delete 2>/dev/null || true
                find workspace/执行日志/截图 -name "*.png" -mtime +3 -delete 2>/dev/null || true
            '''
        }
    }
}

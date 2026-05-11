-- export-users.sql · 100 用户清单导出模板(主宪章 §24 PII scrub)
--
-- 假设你的注册系统是 Postgres / MySQL,字段按需调整.
-- 隐私:GDPR/PIPL/CCPA — user_id 必脱敏(hash),不存真名/邮箱明文.
-- 导出后 30 天删 csv.

-- ============ 1. 基础导出(脱敏)============
SELECT
  -- 脱敏:不用真 id,用 hash 前 8 位
  SUBSTRING(MD5(user_id::text), 1, 8) AS user_hash,
  -- 行业(用户填 / 推断)
  COALESCE(industry, 'unknown') AS industry,
  -- 团队规模档(避免精确数 → 隐私)
  CASE
    WHEN team_size IS NULL THEN 'unknown'
    WHEN team_size = 1 THEN 'solo'
    WHEN team_size BETWEEN 2 AND 5 THEN 'small'
    WHEN team_size BETWEEN 6 AND 20 THEN 'medium'
    ELSE 'large'
  END AS team_size_bucket,
  -- 注册时间(按月聚合 → 隐私)
  DATE_TRUNC('month', registered_at) AS registered_month,
  -- 来源渠道
  acquisition_channel
FROM users
WHERE registered_at >= NOW() - INTERVAL '6 months'
  AND deleted_at IS NULL
ORDER BY registered_at DESC;

-- ============ 2. Skill 使用率(top 10)============
-- 假设 telemetry 表 skill_invocations(user_id, skill_name, ts)
SELECT
  skill_name,
  COUNT(DISTINCT user_id) AS unique_users,
  COUNT(*) AS total_invocations,
  ROUND(COUNT(DISTINCT user_id) * 100.0 / (SELECT COUNT(*) FROM users), 1) AS user_pct
FROM skill_invocations
WHERE ts >= NOW() - INTERVAL '30 days'
GROUP BY skill_name
ORDER BY unique_users DESC
LIMIT 30;

-- ============ 3. 0% 使用率的 skill(必砍候选)============
-- 列出 30 天内无人用的 skill
WITH used AS (
  SELECT DISTINCT skill_name FROM skill_invocations
  WHERE ts >= NOW() - INTERVAL '30 days'
)
SELECT skill_name AS skill_unused
FROM (VALUES
  ('smoke-test'), ('test-coordinator'), ('regression-test'),
  ('testcase-design'), ('python-script-gen'), ('jmeter-script-gen'),
  ('data-preparation'), ('zentao-bug-submission'),
  ('mobile-test'), ('desktop-test'), ('visual-test'),
  ('system-test'), ('ai-test'),
  ('pentest-coordinator'), ('pentest-recon'), ('pentest-vuln'),
  ('pentest-exploit'), ('pentest-web'), ('pentest-api'), ('pentest-report'),
  ('automotive-test'), ('automotive-can-bus-test'),
  ('automotive-adas-scenario'), ('automotive-ota-update-test'),
  ('automotive-hil-loop-test'),
  ('tdd-workflow'), ('verification-loop'), ('e2e-testing'),
  ('eval-harness'), ('security-review'), ('agent-introspection-debugging'),
  ('build-your-own-x-explorer')
) AS all_skills(skill_name)
LEFT JOIN used USING (skill_name)
WHERE used.skill_name IS NULL;

-- ============ 4. 留存(7/14/30 day)============
SELECT
  COUNT(DISTINCT user_id) FILTER (WHERE last_active >= NOW() - INTERVAL '7 days') AS dau_7d,
  COUNT(DISTINCT user_id) FILTER (WHERE last_active >= NOW() - INTERVAL '14 days') AS wau_14d,
  COUNT(DISTINCT user_id) FILTER (WHERE last_active >= NOW() - INTERVAL '30 days') AS mau_30d,
  COUNT(*) AS total_registered
FROM users
WHERE deleted_at IS NULL;

-- ============ 5. Bug 反馈 / Issue 数(投入产出)============
SELECT
  SUBSTRING(MD5(user_id::text), 1, 8) AS user_hash,
  COUNT(*) AS feedback_count,
  MAX(created_at) AS latest_feedback
FROM feedback
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY user_id
HAVING COUNT(*) >= 3
ORDER BY feedback_count DESC
LIMIT 20;

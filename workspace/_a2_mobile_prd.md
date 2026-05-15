# 电商移动应用 PRD (Android APK / iOS)

## 一、项目背景

本项目交付一款跨平台的电商 **mobile app**，目标平台为 **Android** (APK 分发) 与 **iOS** (App Store)。
面向 C 端消费者，提供商品浏览、下单、支付闭环。技术栈选用 React Native，构建产物为 APK / IPA。

## 二、目标用户

- 18-45 岁移动端购物用户
- Android 8.0+ / iOS 14+ 设备持有者

## 三、核心功能

### F1. 用户登录
- 手机号 + 短信验证码登录
- 第三方登录 (微信 / Apple ID)
- Token 持久化于 mobile app 本地安全存储

### F2. 商品列表
- 首页瀑布流展示商品 SKU
- 分类筛选 + 搜索
- 下拉刷新 / 上拉加载更多
- 商品详情页含图文 + 规格选择

### F3. 下单结算
- 加入购物车
- 收货地址管理
- 支付宝 / 微信支付 / Apple Pay (iOS)
- 订单状态追踪

## 四、非功能需求

- APK 包体 < 30MB
- 冷启动 < 2s
- 兼容 Android 8.0+ 与 iOS 14+
- 离线缓存最近浏览商品

## 五、交付物

- Android APK (release signed)
- iOS IPA (TestFlight)
- 自动化测试报告 (Appium / Detox)

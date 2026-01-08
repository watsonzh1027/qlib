---
trigger: always_on
---

1. 在启动console 或运行命令之前，必须激活环境： conda activate qlib
2. 问题解决完成，应该在issues 目录下记录和总结，更新issue文件，持续解决直到状态为 CLOSED
3. 项目的日志在 logs 目录下, 还有 docs, scripts, data, output, 生成的文件按照用途进行目录划分
4. 测试文件只能保存在 tests 目录下, 名称为 test_*.py.  代码修改完成后，必须对当前修改或添加的模块进行单元测试，代码功能覆盖率不低于90%
5. 临时文件保存在 tmp 目录下，使用完成后应该删除
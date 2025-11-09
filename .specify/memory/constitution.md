<!-- Sync Impact Report
Version change: N/A → 1.0.0
List of modified principles: Added I. 测试驱动开发 (Test-Driven Development, TDD), II. 测试覆盖率 (Test Coverage)
Added sections: Core Principles, Development Standards
Removed sections: None
Templates requiring updates: ✅ updated .specify/templates/plan-template.md (Constitution Check)
Follow-up TODOs: None
-->
# qlib-crypto Constitution

## Core Principles

本项目开发遵循**规格驱动开发 (Spec-Driven Development, SDD)** 流程，以确保代码质量、架构一致性和功能完整性。所有开发工作（包括人类和 AI 辅助）都必须遵循本宪章规定的原则。

## Development Standards

### I. 🧪 测试驱动开发 (Test-Driven Development, TDD)

* **TDD 强制要求：** 所有新功能开发、模块创建、错误修复和重构都**必须**严格遵循 TDD 周期（Red-Green-Refactor）。
    * **Red (红灯)：** 必须先编写失败的测试用例（体现预期行为或待修复的 Bug）。
    * **Green (绿灯)：** 编写最少量的代码使测试通过。
    * **Refactor (重构)：** 在测试保护下，优化代码结构和设计，确保所有测试仍然通过。
* **测试范围：** 所有核心业务逻辑和模块功能都必须有对应的单元测试（Unit Tests）和集成测试（Integration Tests）。

* **测试任务：** 所有代码开发任务后，都应该有相应的测试任务， 收到测试通过的确认后， 才可以将任务状态置为 ‘完成’。

### II. 📊 测试覆盖率 (Test Coverage)

* **基线要求：** 任何时间点，项目代码的**总测试覆盖率不得低于 70%**。

## Governance

宪章规定了开发原则和标准。所有PR和代码变更必须验证合规性。复杂性必须有正当理由。

**Version**: 1.0.0 | **Ratified**: 2025-11-08 | **Last Amended**: 2025-11-08

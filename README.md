# DTSynth

DTB逆向还原与跨版本移植工具（RK35xx优先）

## 项目结构

```
├── src/
│   └── dtsynth/          # 核心模块
├── tests/                # 单元测试
├── web/                  # 前端资源（预留）
├── scripts/              # 辅助脚本
├── pyproject.toml        # Poetry配置文件
└── README.md             # 项目说明
```

## 功能特性

- DTB文件解析与逆向工程
- 跨Linux内核版本设备树移植
- 针对RK35xx系列芯片优化支持
- Web界面管理工具

## 依赖说明

- `pylibfdt`: DTB解析核心库
- `fastapi`: Web API框架
- `pydantic`: 数据验证与序列化
- `uvicorn`: ASGI服务器
# CSV Analyzer

一个基于PyQt6开发的大体积CSV查看分析软件，采用前后端分离架构。

## 特性

- 🚀 **大文件支持**: 使用DuckDB和Polars处理GB级CSV文件
- 🎨 **VSCode风格UI**: 现代化深色主题界面
- 📊 **SQL查询**: 快速建立和执行SQL查询
- 📈 **数据分析**: 缺失值统计、数值分布分析
- 💾 **视图保存**: 保存查询结果为视图
- ⚡ **前后端分离**: 后端进程处理计算，前端只负责渲染

## 安装

使用uv安装依赖:

```bash
uv sync
```

## 运行

```bash
uv run csv-analyzer
```

或者:

```bash
uv run python -m csv_analyzer.main
```

## 架构

```
csv_analyzer/
├── backend/           # 后端服务
│   ├── engine.py      # 数据处理引擎
│   ├── sql_executor.py # SQL执行器
│   └── analyzer.py    # 数据分析模块
├── frontend/          # 前端UI
│   ├── main_window.py # 主窗口
│   ├── components/    # UI组件
│   └── styles/        # 样式文件
├── core/              # 核心通信
│   └── ipc.py         # 进程间通信
└── main.py            # 入口文件
```

## 使用说明

1. 点击"打开文件"加载CSV文件
2. 使用左侧导航查看已加载的表
3. 在SQL编辑器中编写查询
4. 使用分析面板查看数据统计
5. 保存常用查询为视图

from pathlib import Path

DEMO = """# 个人资料

张同学，计算机科学与技术专业本科生，关注人工智能和后端工程。

## 项目经历

2025 年担任校园二手交易平台后端负责人，使用 Python、FastAPI 和 PostgreSQL，
完成用户、商品和订单模块，接口平均响应时间降低 35%。

## 比赛经历

参加 2025 年中国大学生计算机设计大赛，负责模型服务和数据处理，获得省级二等奖。

## 实习经历

2025 年暑期在某科技公司担任后端开发实习生，参与日志分析平台建设。

## 学校履历

2022 年进入示例大学计算机学院，主修数据结构、操作系统、数据库和机器学习。
"""


def main() -> None:
    path = Path("data/demo-profile.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEMO, encoding="utf-8")
    print(path.resolve())


if __name__ == "__main__":
    main()

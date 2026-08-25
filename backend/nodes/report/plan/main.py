from sage.models.node import ReportPlanInput, ReportPlanOutput
from sage.report.plan_tools import finalize_plan_tools
from sage.nodes import node, NodeV
from sage.report.validators import PlanStructureValidator

@node(input=ReportPlanInput, output=ReportPlanOutput)
class Plan(NodeV):
    def __init__(self):
        super().__init__(validators=[PlanStructureValidator()])

    async def run(self, **kwargs):
        api_tools = list(kwargs.get("tools") or [])
        plan: ReportPlanOutput = await super().run(**kwargs)
        plan = finalize_plan_tools(
            plan,
            api_tools,
            data_id=kwargs.get("data_id"),
        )
        if api_tools:
            missing = [p for p in api_tools if p not in (plan.tools or [])]
            if missing:
                raise ValueError(
                    f"API tools {missing} 가 plan.tools 에 반영되지 않았습니다: {plan.tools}"
                )
        return plan

async def test():
    plan = Plan()
    res: ReportPlanOutput = await plan.run(
        data_id="did-stock-data-b09bdfdd",
        tools=["kis/stock"],
        query=(
            "data\n"
            "code: 종목 코드\n"
            "~: 기타 필드가 있다고 가정\n"
            "위 데이터 분석하여 저 per,pbr 시가총액 상위 10개 종목 추천 보고서"
        ),
    )
    print(res.model_dump_json(indent=2))

if __name__ == "__main__":
    import asyncio

    asyncio.run(test())

class MasterDecisionEngine:

    def decide(self, results):
        if not results:
            return None

        decisions = []

        for result in results:
            decisions.append({
                "strategy": result.strategy_name,
                "data": result.data
            })

        return {
            "status": "COLLECTED",
            "strategies": decisions
        }

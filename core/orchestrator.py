from core.result import StrategyResult
from core.result_manager import ResultManager
from core.master_decision import MasterDecisionEngine


class Orchestrator:

    def __init__(self, strategy_manager):
        self.strategy_manager = strategy_manager
        self.result_manager = ResultManager()
        self.master_decision = MasterDecisionEngine()

    def run_strategy(self, strategy_name, inputs):
        strategy = self.strategy_manager.get(strategy_name)

        result = strategy.run(inputs)

        strategy_result = StrategyResult(
            strategy_name,
            result
        )

        self.result_manager.add(
            strategy_result
        )

        return strategy_result

    def run_strategies(self, strategy_names, inputs):
        results = []

        for strategy_name in strategy_names:
            result = self.run_strategy(
                strategy_name,
                inputs
            )

            results.append(result)

        return results

    def make_master_decision(self):
        results = self.result_manager.get_all()

        return self.master_decision.decide(
            results
        )

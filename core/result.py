class StrategyResult:

    def __init__(self, strategy_name, data):
        self.strategy_name = strategy_name
        self.data = data

    def to_dict(self):
        return {
            "strategy": self.strategy_name,
            "data": self.data
        }

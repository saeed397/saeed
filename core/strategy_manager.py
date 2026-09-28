class StrategyManager:

    def __init__(self):
        self.strategies = {}

    def register(self, name, strategy):
        if not name:
            raise ValueError(
                "Strategy name cannot be empty."
            )

        if strategy is None:
            raise ValueError(
                f"Strategy '{name}' cannot be None."
            )

        if name in self.strategies:
            raise ValueError(
                f"Strategy '{name}' is already registered."
            )

        if not hasattr(strategy, "run"):
            raise TypeError(
                f"Strategy '{name}' must have a run() method."
            )

        self.strategies[name] = strategy

    def get(self, name):
        strategy = self.strategies.get(name)

        if strategy is None:
            raise ValueError(
                f"Strategy '{name}' not found."
            )

        return strategy

    def list_strategies(self):
        return list(self.strategies.keys())

from models.firewall_rule import FirewallRule


class FirewallRuleService:
    """
    Gerencia regras dentro do aplicativo.
    """

    def __init__(self):

        self.rules = []

    # ----------------------------------------
    def add_rule(self, name, port, protocol, action):

        rule = FirewallRule(name, port, protocol, action)

        self.rules.append(rule)

        return rule

    # ----------------------------------------
    def remove_rule(self, name):

        self.rules = [
            r for r in self.rules
            if r.name != name
        ]

    # ----------------------------------------
    def list_rules(self):

        return self.rules
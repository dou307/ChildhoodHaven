from app.domain.models import RiskLevel, SafetyResult

URGENT_SIGNALS = {
    "不想活": "出现自我伤害或死亡表达",
    "想死": "出现自我伤害或死亡表达",
    "杀了": "出现严重伤害表达",
    "流血": "可能存在正在发生的身体伤害",
    "救命": "可能存在正在发生的紧急危险",
    "不要告诉爸爸妈妈": "出现要求隐瞒的重要信号",
}

WATCH_SIGNALS = {
    "每天都欺负": "可能存在持续欺凌",
    "不敢回家": "可能存在家庭或环境安全风险",
    "打我": "可能存在身体冲突",
    "很久都不开心": "可能存在持续低落",
}


def screen_safety(message: str) -> SafetyResult:
    urgent = [signal for signal in URGENT_SIGNALS if signal in message]
    if urgent:
        return SafetyResult(
            risk_level=RiskLevel.URGENT,
            matched_signals=urgent,
            reason="；".join(URGENT_SIGNALS[item] for item in urgent),
        )

    watch = [signal for signal in WATCH_SIGNALS if signal in message]
    if watch:
        return SafetyResult(
            risk_level=RiskLevel.WATCH,
            matched_signals=watch,
            reason="；".join(WATCH_SIGNALS[item] for item in watch),
        )

    return SafetyResult(
        risk_level=RiskLevel.NONE,
        reason="未检测到预设的高风险信号",
    )

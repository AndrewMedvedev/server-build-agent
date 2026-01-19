from langchain.agents import AgentState
from playwright.async_api import Page
from pydantic import BaseModel, Field


class ChoiseGPU(BaseModel):
    price: int = Field(description="Стоимость")
    name: str = Field(description="Название выбранной видеокарты")
    description: str = Field(description="Обоснование выбора")
    key_characteristics: dict[str, str] = Field(
        description="Ключевые характеристики для AI",
    )


class ChoiseCPU(BaseModel):
    price: int = Field(description="Стоимость")
    name: str = Field(description="Название выбранного процессора")
    description: str = Field(description="Обоснование выбора")
    key_characteristics: dict[str, str] = Field(
        description="Ключевые характеристики для AI",
    )


class ChoiseRAM(BaseModel):
    price: int = Field(description="Стоимость")
    name: str = Field(description="Название выбранной оперативной памяти")
    description: str = Field(description="Обоснование выбора")
    key_characteristics: dict[str, str] = Field(
        description="Ключевые характеристики для AI",
    )


class ChoiseSSD(BaseModel):
    price: int = Field(description="Стоимость")
    name: str = Field(description="Название выбранного ssd")
    description: str = Field(description="Обоснование выбора")
    key_characteristics: dict[str, str] = Field(
        description="Ключевые характеристики для AI",
    )


class ComponentAnalysis(BaseModel):
    """Анализ отдельного компонента"""

    component_name: str = Field(..., description="Название компонента")
    current_spec: str = Field(..., description="Текущая спецификация")
    analysis: str = Field(..., description="Анализ компонента")
    score: int = Field(ge=1, le=10, description="Оценка от 1 до 10")
    suggestions: list[str] | None = Field(None, description="Предложения по улучшению")


class BudgetAnalysis(BaseModel):
    """Анализ бюджета"""

    budget_adequacy: str = Field(..., description="Достаточность бюджета")
    price_performance_ratio: str = Field(..., description="Соотношение цена/производительность")
    cost_optimization_suggestions: list[str] | None = Field(
        None, description="Предложения по оптимизации затрат"
    )
    estimated_total_cost: str | None = Field(None, description="Примерная общая стоимость")


class ServerAnalysisResponse(BaseModel):
    """Ответ анализа конфигурации сервера AI/ML"""

    # 1) Резюме
    summary: str = Field(..., description="Краткое резюме конфигурации")
    overall_score: int = Field(ge=1, le=10, description="Общая оценка от 1 до 10")

    # 2) Детальный анализ по компонентам
    components_analysis: list[ComponentAnalysis] = Field(
        ..., description="Подробный анализ каждого компонента"
    )

    # 3) Преимущества для AI/ML
    ml_advantages: list[str] = Field(..., description="Преимущества для задач машинного обучения")

    # 4) Недостатки/бутылочные горлышки
    bottlenecks: list[str] = Field(..., description="Выявленные узкие места и недостатки")

    # 5) Оценка бюджета и цены
    budget_analysis: BudgetAnalysis = Field(..., description="Анализ бюджета и стоимости")

    # 6) Итоговая рекомендация
    final_recommendation: str = Field(..., description="Итоговая рекомендация")
    recommendation_type: str = Field(..., description="Тип рекомендации: approve, modify, reject")

    # Дополнительные поля
    ideal_use_cases: list[str] = Field(..., description="Идеальные варианты использования")
    limitations: list[str] = Field(..., description="Ограничения и риски")
    upgrade_paths: list[str] | None = Field(None, description="Возможные пути улучшения")


class State(AgentState):
    page: Page
    url: str
    navigate: str
    click: str
    fill: str
    evaluate: str
    get_html_content: str
    get_html_part: str
    gpu: ChoiseGPU

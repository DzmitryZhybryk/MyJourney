from app.composition.events import EVENT_SUBSCRIPTIONS
from app.composition.tasks import TASK_BLUEPRINTS


def test_every_subscription_names_a_task_the_worker_registers() -> None:
    """Каждая задача из таблицы подписок есть в blueprint'ах воркера, иначе её поставят, но не исполнят."""
    registered_task_names = {task_name for blueprint in TASK_BLUEPRINTS for task_name in blueprint.tasks}
    subscribed_task_names = {task_name for task_names in EVENT_SUBSCRIPTIONS.values() for task_name in task_names}

    assert subscribed_task_names
    assert subscribed_task_names <= registered_task_names

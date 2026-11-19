"""
Имена procrastinate-задач домена auth — стабильный контракт между слоями.

Имя задачи принадлежит application: сервис диспатчит задачу по имени через
``TaskBusPort`` (не импортируя объект задачи из infra), а infra регистрирует
обработчик под этим же именем (``@task(name=...)``), импортируя константу
отсюда. Направление зависимости — ``infra → application``, как и у портов.
"""

SEND_VERIFICATION_EMAIL_TASK = "auth.send_verification_email"

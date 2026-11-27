from app.shared.exceptions import InvariantViolationError


class StaleRowVersionError(InvariantViolationError):
    """
    UPDATE по ожидаемой версии не нашёл строку: её изменили после чтения.

    Значит, писатель прочитал строку без ``FOR UPDATE`` либо изменил сущность больше одного раза между
    чтением и записью.
    """

    message = "Версия строки устарела"

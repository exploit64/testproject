# language: ru
@all
Функция: UI

  Сценарий: Отсортировать по любому столбцу и проверить сортировку
    Пусть пользователь admin1 авторизуется в админке
    Если пользователь открывает список игроков
    То открывается страница PLAYER MANAGEMENT
    Если пользователь нажимает на ссылку External ID
    То таблица PLAYER MANAGEMENT отсортирована по колонке External ID в порядке STRING_ASC

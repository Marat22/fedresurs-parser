@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo Сейчас будут сохранены ссылки сообщений, которые надо запарсить
echo.

:: Активация виртуального окружения
echo Активация виртуального окружения...
call ../venv/Scripts/activate

:: Запрос о необходимости пересоздания файла
echo.
echo Файл 2month_links.json будет пересоздан, если:
echo - вы запрашиваете данные за другой период времени
echo - вы запрашиваете данные для другой компании
echo - вы явно укажете необходимость пересоздания
echo.
set /p force_recreate="Пересоздать файл 2month_links.json? (y/N): "
if /i "!force_recreate!" == "y" (
    set force_param=--force-recreate
    echo Файл будет пересоздан
) else (
    set force_param=
    echo Будет использован существующий файл (если имеется)
)

:: Запуск основного скрипта
echo.
echo Запуск скрипта подготовки ссылок сообщений...
python ../2prepare_message_links.py !force_param!

:: Проверка результата выполнения
if !errorlevel! equ 0 (
    echo.
    echo Успешно завершено!
    echo Ссылки на сообщения сохранены в 2month_links.json
) else (
    echo.
    echo Ошибка при выполнении скрипта (код: !errorlevel!)
)

pause
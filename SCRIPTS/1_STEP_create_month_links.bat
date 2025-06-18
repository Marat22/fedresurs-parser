@echo off
setlocal enabledelayedexpansion

:: 1. Активация среды
echo Активация виртуального окружения...
call ../venv/Scripts/activate

:: 2. Запрос наименования компании
echo.
set /p company_name="Введите наименование компании (без лишних пробелов): "
if "!company_name!" == "" (
    echo Ошибка: название компании не может быть пустым
    pause
    exit /b 1
)

:: 3. Запрос месяца начала скачивания
echo.
set /p start_month="Введите месяц начала скачивания данных (формат YYYY-MM, по умолчанию 2023-04): "
if "!start_month!" == "" set start_month=2023-04

:: 4. Запрос месяца окончания скачивания
:: Получаем текущий месяц в формате YYYY-MM
for /f "tokens=1,2 delims=/" %%a in ('date /t') do (
    set current_year=%%c
    set current_month=%%b
)
if "!current_month!" == "" (
    for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do (
        set current_year=%%a:~0,4%
        set current_month=%%a:~4,2%
    )
)
set current_date=!current_year!-!current_month!

echo.
set /p end_month="Введите месяц окончания скачивания данных (формат YYYY-MM, по умолчанию %current_date%): "
if "!end_month!" == "" set end_month=%current_date%

:: 5. Запуск скрипта с параметрами
echo.
echo Запуск скрипта с параметрами:
echo Поиск: !company_name!
if "!start_month!" == "2023-04" (
    if "!end_month!" == "%current_date%" (
        echo Используются даты по умолчанию (2023-04 - текущий месяц)
        python ../1prepare_month_links.py "!company_name!"
    ) else (
        echo Начало: по умолчанию (2023-04), Конец: !end_month!
        python ../1prepare_month_links.py "!company_name!" --end "!end_month!"
    )
) else (
    if "!end_month!" == "%current_date%" (
        echo Начало: !start_month!, Конец: по умолчанию (текущий месяц)
        python ../1prepare_month_links.py "!company_name!" --start "!start_month!"
    ) else (
        echo Начало: !start_month!, Конец: !end_month!
        python ../1prepare_month_links.py "!company_name!" --start "!start_month!" --end "!end_month!"
    )
)

:: Проверка кода завершения
if !errorlevel! equ 0 (
    echo.
    echo Успешно завершено!
    echo Был создан файл 1month_links.json
) else (
    echo.
    echo Ошибка при выполнении скрипта (код: !errorlevel!)
)

pause
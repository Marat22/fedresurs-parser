@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: 1. Activate environment
echo Активация виртуального окружения...
call ../venv/Scripts/activate

:: 2. Get company name
echo.
set /p company_name="Введите наименование компании (без лишних пробелов): "
if "!company_name!" == "" (
    echo Ошибка: название компании не может быть пустым
    pause
    exit /b 1
)

:: 3. Get start month (default empty)
echo.
set /p start_month="Введите месяц начала скачивания данных (формат YYYY-MM, по умолчанию пропустить): "
if "!start_month!" == "" (
    set start_param=
) else (
    set start_param=--start "!start_month!"
)

:: 4. Get end month (default empty)
for /f "tokens=1-3 delims=-" %%a in ('powershell -command "Get-Date -Format 'yyyy-MM-dd'"') do (
    set current_year=%%a
    set current_month=%%b
)
set current_date=!current_year!-!current_month!

echo.
set /p end_month="Введите месяц окончания скачивания данных (формат YYYY-MM, по умолчанию пропустить): "
if "!end_month!" == "" (
    set end_param=
) else (
    set end_param=--end "!end_month!"
)

:: 5. Run script with only specified parameters
echo.
echo Запуск скрипта с параметрами:
echo Поиск: !company_name!

if defined start_param echo Начало: !start_month!
if defined end_param echo Конец: !end_month!

:: Build command dynamically
set py_command=python ../1prepare_month_links.py "!company_name!"
if defined start_param set py_command=!py_command! !start_param!
if defined end_param set py_command=!py_command! !end_param!

echo Выполняется: !py_command!
!py_command!

:: Check exit code
if !errorlevel! equ 0 (
    echo.
    echo Успешно завершено!
    echo Был создан файл 1month_links.json
    pause
) else (
    echo.
    echo Ошибка при выполнении скрипта (код: !errorlevel!)
    pause
    exit /b !errorlevel!
)
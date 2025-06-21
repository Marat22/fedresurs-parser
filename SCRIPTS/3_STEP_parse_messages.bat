@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: Get the directory where this batch file is located
set "batch_dir=%~dp0"

:: Main header
echo ______________________________________________________________________________
echo          ВНИМАНИЕ: ЭТАП СБОРА СЫРЫХ ДАННЫХ ИЗ ФЕДРЕСУРСА
echo ______________________________________________________________________________
echo Сейчас будет заполняться папка 3raw_contents
echo Это может занять несколько часов
echo ______________________________________________________________________________
echo.

:: Activate Python environment
echo Активируем виртуальное окружение...
call "%batch_dir%..\venv\Scripts\activate"

:: Browser mode selection
:select_browser
echo.
echo Выберите режим браузера:
echo [1] Видимый режим (рекомендуется)
echo [2] Скрытый режим
set /p "browser_mode=Введите 1 или 2: "

if "%browser_mode%"=="1" (
    set "options=--show"
    goto select_folder
) else if "%browser_mode%"=="2" (
    set "options="
    goto select_folder
) else (
    echo Неверный ввод
    goto select_browser
)

:: Folder option selection
:select_folder
echo.
echo Опции для папки 3raw_contents:
echo [1] Использовать существующие данные
echo [2] Удалить и создать заново
set /p "folder_option=Введите 1 или 2: "

if "%folder_option%"=="1" (
    goto run_script
) else if "%folder_option%"=="2" (
    set "options=%options% --force-recreate"
    goto run_script
) else (
    echo Неверный ввод
    goto select_folder
)

:: Run the script
:run_script
echo.
echo Запускаем сбор данных...
echo Команда: python "%batch_dir%..\3prepare_raw_contents.py" %options%
echo.
pause

python "%batch_dir%..\3prepare_raw_contents.py" %options%

:: Show results
if %errorlevel% equ 0 (
    echo.
    echo УСПЕШНО ЗАВЕРШЕНО
) else (
    echo.
    echo ОШИБКА: код %errorlevel%
)

pause
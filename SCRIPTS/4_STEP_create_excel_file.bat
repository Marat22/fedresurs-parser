@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: Get the directory where this batch file is located
set "batch_dir=%~dp0"

echo ______________________________________________________________________________
echo          СОЗДАНИЕ ИТОГОВОГО EXCEL-ФАЙЛА
echo ______________________________________________________________________________
echo Обработка данных из папки 3raw_contents...
echo Результат будет сохранён в output.xlsx
echo ______________________________________________________________________________
echo.

:: Активируем Python-окружение
echo Активируем виртуальное окружение...
call "%batch_dir%..\venv\Scripts\activate"

:: Запускаем скрипт генерации Excel
python "%batch_dir%..\4make_excel_files.py"

:: Проверяем результат
if exist "%batch_dir%..\output.xlsx" (
    for /f %%F in ('dir /a-d /os "%batch_dir%..\output.xlsx" ^| find "output.xlsx"') do set "filesize=%%~zF"
    echo.
    echo ______________________________________________________________________________
    echo ✔ Файл output.xlsx успешно создан!
    echo Размер: !filesize! байт
    echo ______________________________________________________________________________

    :: Предлагаем открыть файл
    echo.
    set /p open_file="Открыть файл output.xlsx сейчас? (Y - да / N - нет): "
    if /i "!open_file!" == "Y" (
        start "" "%batch_dir%..\output.xlsx"
        echo Файл открыт в программе по умолчанию!
    )
) else (
    echo.
    echo ______________________________________________________________________________
    echo ❌ Ошибка! Файл output.xlsx не создан!
    echo Проверьте:
    echo 1. Наличие данных в папке 3raw_contents
    echo 2. Логи скрипта 4make_excel_files.py
    echo ______________________________________________________________________________
)

pause
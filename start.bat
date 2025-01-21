@REM @echo off
@REM echo Iniciando CoffeeAI...
@REM cd dist\CoffeeAI
@REM start CoffeeAI.exe
@REM echo Servidor iniciado! 
@REM echo Aguarde alguns segundos e acesse http://localhost:5000 no seu navegador
@REM pause

@echo off
echo Iniciando CoffeeAI...
cd dist
if exist "CoffeeAI\CoffeeAI.exe" (
    cd CoffeeAI
    start CoffeeAI.exe
    echo Servidor iniciado! 
    echo Aguarde alguns segundos e acesse http://localhost:5000 no seu navegador
) else (
    echo Erro: Executavel nao encontrado. 
    echo Certifique-se de que o programa foi compilado corretamente.
)
pause
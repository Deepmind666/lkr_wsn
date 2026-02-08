@echo off
REM AERIS项目环境快速修复脚本
REM 作者: Claude
REM 日期: 2025-10-19

echo ========================================
echo AERIS项目环境快速修复
echo ========================================
echo.

echo 步骤1: 激活conda环境...
call C:\Users\admin\anaconda3\Scripts\activate.bat aeris-py311

echo.
echo 步骤2: 切换到项目目录...
cd /d C:\AERIS-WSN-Protocol

echo.
echo 步骤3: 安装依赖...
pip install -r requirements.txt

echo.
echo 步骤4: 验证安装...
python scripts/verify_dependencies.py

echo.
echo 步骤5: 运行快速测试...
python scripts/smoke_test.py

echo.
echo ========================================
echo 修复完成！
echo ========================================
pause

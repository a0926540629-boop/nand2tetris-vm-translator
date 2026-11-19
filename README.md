# Nand2Tetris VM Translator
本專案為 Nand2Tetris 的 VM 轉譯器，使用 Python 實作，可以把 VM 指令轉成 Hack 組合語言。

支援指令：
- 算術邏輯：add、sub、neg、eq、gt、lt、and、or、not
- 記憶體操作：push、pop
- 流程控制：label、goto、if-goto
- 函式：function、call、return

測試檔案：
1. `SimpleAdd.vm`：push constant 7、push constant 8、add，執行完堆疊頂端結果為 15
2. `SimpleFunction.vm`：標準函式測試案例，包含 local、argument、add、sub、not、return

檔案清單
- `vm.py`：轉譯主程式
- SimpleAdd.vm / SimpleAdd.asm
- SimpleFunction.vm / SimpleFunction.asm

執行方式
```bash
python vm.py SimpleAdd.vm
python vm.py SimpleFunction.vm

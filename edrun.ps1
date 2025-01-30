Copy-Item ./edcore.py ./edcore-running.py
./edcore-running.py $args
Remove-Item ./edcore-running.py

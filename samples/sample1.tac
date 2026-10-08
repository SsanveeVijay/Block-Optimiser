# loop with foldable constants
a = 2 + 3
b = a * 4
i = 0
L1:
if i >= 10 goto L2
t = b + i
i = i + 1
goto L1
L2:
c = 10 / 3
d = c % 2
return d

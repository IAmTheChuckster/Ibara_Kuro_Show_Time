; DIP SWITCH SETTING: draw "ranking save" (row 10) and then the new "bomb counts" line (row 12).
; The menu's call to the ranking-save line (literal at 0x0C0654B0) is pointed here.  @ 0x0C05B700
MENU:
  sts.l pr,@-r15
  mov.l @RANK,r0
  jsr @r0               ; ranking save: row 10, column 3 (r4/r5 from the caller)
  nop
  mov.l @BOMB,r0
  mov #12,r4
  jsr @r0               ; bomb counts (old "difficulty2" line routine): row 12, column 3
  mov #3,r5
  lds.l @r15+,pr
  rts
  nop
  nop
RANK: .long 0x0C065EA0
BOMB: .long 0x0C068920

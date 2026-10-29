; Test mode, every frame of the menu loop (bsr at 0x0C062808 -> stub 0x0C0629B4 -> here):
; switch Dyne mode off so the test menu always uses the normal controls, then redo the two
; replaced literal loads (r8 = 0x0C060BC0, r11 = 0x0C061200).  r0 is free.  @ 0x0C05B6E0
TESTM:
  mov.l @STATE,r0
  mov #0,r8
  mov.l r8,@r0          ; Dyne flag, Start held, select counter = 0
  mov.l @F1,r8
  mov.l @F2,r11         ; (not in the rts delay slot: PC-relative loads there read the
  rts                   ;  wrong address)
  nop
  .align 4
STATE: .long 0x0C05B4F0
F1: .long 0x0C060BC0
F2: .long 0x0C061200

; New game (bsr at 0x0C06A7B4 -> stub 0x0C06AE44 -> here; the bsr delay slot keeps
; "mov.l r0,@r7"): redo the replaced "mov.l r0,@(4,r7)" (r0 = 0), switch Dyne mode off and
; count Start as held, so the press that started the game must be released before it can
; switch.  @ 0x0C05B640
NEWGAME:
  mov #0,r0
  .word 0x1701          ; mov.l r0,@(4,r7)
  mov.l r1,@-r15
  mov.l @STATE,r1
  mov #1,r0
  mov.b r0,@(1,r1)      ; Start held
  mov #0,r0
  mov.b r0,@r1          ; Dyne mode off
  rts
  mov.l @r15+,r1
  .align 4
STATE: .long 0x0C05B4F0

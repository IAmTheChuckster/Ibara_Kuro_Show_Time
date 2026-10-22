; Ship select, once per frame (bsr at 0x0C0B8390 -> stub 0x0C0B8384 -> here): mark "select
; active" for the control routine, then redo the two replaced instructions
; (r2 = select timer address, r1 = timer).  @ 0x0C05B600
MARK:
  mov.l @SELF,r2
  mov #3,r1
  mov.b r1,@r2
  mov.l @TIMER,r2
  rts
  mov.l @r2,r1
  .align 4
SELF: .long 0x0C05B4F2
TIMER: .long 0x0C238014

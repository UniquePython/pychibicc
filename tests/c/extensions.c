#include "test.h"

// Tests for dight's non-standard extensions to chibicc: _Unless,
// _Until, _Loop, _Forever, _Infer, and _Constexpr, plus comment support.

int ret3()
{
  return 3;
}

int forever_test()
{
  int i = 0;
  _Forever
  {
    i = i + 1;
    if (i == 5)
      return i;
  }
}

int main()
{
  // _Unless: sugar for "if (!expr)".
  ASSERT(2, ({ int x; _Unless (0) x=2; else x=3; x; }));
  ASSERT(2, ({ int x; _Unless (1-1) x=2; else x=3; x; }));
  ASSERT(3, ({ int x; _Unless (1) x=2; else x=3; x; }));
  ASSERT(3, ({ int x; _Unless (2-1) x=2; else x=3; x; }));

  // _Until: sugar for "while (!expr)".
  ASSERT(11, ({ int i=0; _Until(i>10) i=i+1; i; }));

  // _Loop(n): run the body exactly n times. n is evaluated once, up front.
  ASSERT(10, ({ int i=0; _Loop(10) i=i+1; i; }));
  ASSERT(0, ({ int i=0; _Loop(0) i=i+1; i; }));
  ASSERT(55, ({ int i=0; int j=0; _Loop(10) {i=i+1; j=i+j;} j; }));
  ASSERT(5, ({ int r; _Loop(5) r=5; r; }));
  ASSERT(3, ({ int n=3; int i=0; _Loop(n) i=i+1; i; }));
  ASSERT(9, ({ int i=0; _Loop(3) _Loop(3) i=i+1; i; }));

  // _Forever: sugar for "for (;;)". Tested via a helper function that
  // returns from inside the loop, since a bare "return" inside a
  // statement expression would return from main itself.
  ASSERT(5, forever_test());

  // _Infer: declares a local whose type is inferred from its initializer.
  ASSERT(5, ({ _Infer x = 5; x; }));
  ASSERT(7, ({ _Infer x = 5; _Infer y = x + 2; y; }));
  ASSERT(10, ({ int a = 10; _Infer p = &a; *p; }));
  ASSERT(65, ({ char c = 65; _Infer x = c; x; }));
  ASSERT(3, ({ _Infer x = ret3(); x; }));
  ASSERT(55, ({ _Infer i = 0; _Infer j = 0; _Loop(10) {i = i+1; j = i+j;} j; }));
  ASSERT(32, ({ _Infer x = 5; sizeof(x) * 4; }));
  ASSERT(1, ({ _Infer x = 3; _Infer y = 4; x < y; }));

  // _Constexpr: folds a constant expression at compile time.
  ASSERT(14, _Constexpr(2 + 3 * (10 - 6)));
  ASSERT(12, _Constexpr(_Constexpr(2 + 2) * 3));
  ASSERT(5, _Constexpr(-5 + 10));

  ASSERT(1, _Constexpr(3 == 3));
  ASSERT(0, _Constexpr(3 == 4));
  ASSERT(0, _Constexpr(3 != 3));
  ASSERT(1, _Constexpr(3 != 4));

  ASSERT(1, _Constexpr(2 < 3));
  ASSERT(0, _Constexpr(3 < 3));
  ASSERT(0, _Constexpr(4 < 3));

  ASSERT(1, _Constexpr(2 <= 3));
  ASSERT(1, _Constexpr(3 <= 3));
  ASSERT(0, _Constexpr(4 <= 3));

  ASSERT(1, _Constexpr(3 > 2));
  ASSERT(0, _Constexpr(3 > 3));
  ASSERT(0, _Constexpr(3 > 4));

  ASSERT(1, _Constexpr(3 >= 2));
  ASSERT(1, _Constexpr(3 >= 3));
  ASSERT(0, _Constexpr(3 >= 4));

  ASSERT(1, _Constexpr(1 + 1 == 2));
  ASSERT(1, _Constexpr((5 - 2) * 2 >= 6));
  ASSERT(0, _Constexpr(_Constexpr(2 * 3) != 6));

  // Line and block comments.
  ASSERT(2, ({ /* return 1; */ 2; })); // trailing line comment

  printf("OK\n");
  return 0;
}

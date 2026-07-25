#!/bin/bash

build_dir="build"
mkdir -p "$build_dir/att" "$build_dir/intel"

test_num=0

assert() {
    expected="$1"
    input="$2"
    test_num=$((test_num + 1))

    for syntax in att intel; do
        asm_file="$build_dir/$syntax/test${test_num}.s"
        bin_file="$build_dir/$syntax/test${test_num}"

        python3 main.py "$input" "$syntax" > "$asm_file" || exit 1
        gcc -static -o "$bin_file" "$asm_file"
        "$bin_file"
        actual="$?"

        if [ "$actual" = "$expected" ]; then
            echo "[$syntax] $input => $actual"
        else
            echo "[$syntax] $input => expected $expected, but got $actual"
            exit 1
        fi
    done
}

assert 0 '0;'
assert 42 '42;'
assert 21 '5+20-4;'
assert 41 ' 12 + 34 - 5 ;'
assert 47 '5+6*7;'
assert 15 '5*(9-6);'
assert 4 '(3+5)/2;'
assert 10 '-10+20;'
assert 10 '- -10;'
assert 10 '- - +10;'

assert 0 '0==1;'
assert 1 '42==42;'
assert 1 '0!=1;'
assert 0 '42!=42;'

assert 1 '0<1;'
assert 0 '1<1;'
assert 0 '2<1;'
assert 1 '0<=1;'
assert 1 '1<=1;'
assert 0 '2<=1;'

assert 1 '1>0;'
assert 0 '1>1;'
assert 0 '1>2;'
assert 1 '1>=0;'
assert 1 '1>=1;'
assert 0 '1>=2;'

assert 3 'a=3; a;'
assert 8 'a=3; z=5; a+z;'

assert 3 'a=3; a;'
assert 8 'a=3; z=5; a+z;'
assert 6 'a=b=3; a+b;'
assert 3 'foo=3; foo;'
assert 8 'foo123=3; bar=5; foo123+bar;'

echo OK
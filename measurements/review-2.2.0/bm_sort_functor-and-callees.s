<(anonymous namespace)::BM_SortFunctor(benchmark::State&) [clone .cold]>:
mov    %r13,%rdi
call   ADDR <std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >::_M_dispose()>
lea    0x60(%rsp),%rdi
call   ADDR <std::_Vector_base<minidaq::Single, std::allocator<minidaq::Single> >::~_Vector_base()>
mov    0x38(%rsp),%rdi
call   ADDR <std::_Vector_base<minidaq::Single, std::allocator<minidaq::Single> >::~_Vector_base()>
mov    0xa8(%rsp),%rax
sub    %fs:0x28,%rax
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&) [clone .cold]+OFF>
mov    %rbx,%rdi
call   ADDR <_Unwind_Resume@plt>
call   ADDR <__stack_chk_fail@plt>

<(anonymous namespace)::BM_SortFunctor(benchmark::State&)>:
endbr64
push   %r15
xor    %edx,%edx
push   %r14
push   %r13
push   %r12
mov    %rdi,%r12
push   %rbp
push   %rbx
sub    $0xb8,%rsp
mov    %fs:0x28,%rax
mov    %rax,0xa8(%rsp)
mov    0x20(%rdi),%rax
lea    0x40(%rsp),%rdi
mov    %rdi,0x38(%rsp)
mov    (%rax),%rbx
cmpq   $0x1,0x8(%rax)
sete   %dl
mov    %rbx,%rsi
mov    %rbx,0x10(%rsp)
shl    $0x6,%rsi
call   ADDR <(anonymous namespace)::make_batches(unsigned long, bool)>
shr    $0x3b,%rbx
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
pxor   %xmm0,%xmm0
cmpq   $0x0,0x10(%rsp)
movups %xmm0,0x68(%rsp)
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    0x10(%rsp),%rbx
shl    $0x4,%rbx
mov    %rbx,%rdi
mov    %rbx,0x30(%rsp)
call   ADDR <operator new(unsigned long)@plt>
lea    (%rax,%rbx,1),%rdx
mov    %rax,0x60(%rsp)
mov    %rdx,0x70(%rsp)
nopl   0x0(%rax,%rax,1)
movq   $0x0,(%rax)
add    $0x10,%rax
movl   $0x0,-0x8(%rax)
movl   $0x0,-0x4(%rax)
cmp    %rdx,%rax
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    0x1c(%r12),%eax
mov    %rdx,0x68(%rsp)
test   %eax,%eax
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    %r12,%rdi
mov    0x10(%r12),%r13
call   ADDR <benchmark::State::StartKeepRunning()>
mov    %r13,0x18(%rsp)
xor    %ebp,%ebp
test   %r13,%r13
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
nopl   (%rax)
mov    %r12,%rdi
call   ADDR <benchmark::State::PauseTiming()>
cmpq   $0x0,0x10(%rsp)
mov    0x60(%rsp),%rbx
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
add    $0x1,%rbp
mov    %r12,%rdi
and    $0x3f,%ebp
call   ADDR <benchmark::State::ResumeTiming()>
mov    0x68(%rsp),%r14
cmp    %r14,%rbx
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    %r14,%r13
sub    %rbx,%r13
mov    %r13,%rax
sar    $0x4,%rax
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
bsr    %rax,%rdx
mov    %r14,%rsi
mov    %rbx,%rdi
movslq %edx,%rdx
add    %rdx,%rdx
call   ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)>
lea    0x10(%rbx),%rdx
cmp    $0x100,%r13
jle    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
lea    0x100(%rbx),%r15
mov    %rbp,0x20(%rsp)
mov    %rdx,%r13
mov    %r12,0x28(%rsp)
mov    %r15,%rbp
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
nopl   0x0(%rax,%rax,1)
cmp    0x8(%rbx),%r12d
jae    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    %r13,%rdx
movss  0xc(%r13),%xmm0
sub    %rbx,%rdx
cmp    $0x10,%rdx
jle    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    $0x10,%edi
mov    %rbx,%rsi
movss  %xmm0,0xc(%rsp)
sub    %rdx,%rdi
add    %r13,%rdi
call   ADDR <memmove@plt>
movss  0xc(%rsp),%xmm0
add    $0x10,%r13
mov    %r15,(%rbx)
mov    %r12d,0x8(%rbx)
movss  %xmm0,0xc(%rbx)
cmp    %rbp,%r13
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    0x0(%r13),%r15
mov    0x8(%r13),%r12d
cmp    (%rbx),%r15
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
jl     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    %r13,%rax
movss  0xc(%r13),%xmm0
cmp    -0x10(%rax),%r15
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
cmp    -0x8(%rax),%r12d
jae    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
movdqu -0x10(%rax),%xmm2
sub    $0x10,%rax
movups %xmm2,0x10(%rax)
cmp    -0x10(%rax),%r15
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
jl     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
add    $0x10,%r13
mov    %r15,(%rax)
mov    %r12d,0x8(%rax)
movss  %xmm0,0xc(%rax)
cmp    %rbp,%r13
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    0x20(%rsp),%rbp
mov    0x28(%rsp),%r12
cmp    %r13,%r14
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    %r13,%rdx
mov    %rdx,%rax
mov    (%rdx),%rcx
mov    0x8(%rdx),%esi
movss  0xc(%rdx),%xmm0
cmp    -0x10(%rax),%rcx
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
cmp    -0x8(%rax),%esi
jae    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
movdqu -0x10(%rax),%xmm1
sub    $0x10,%rax
movups %xmm1,0x10(%rax)
cmp    -0x10(%rax),%rcx
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
jl     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
add    $0x10,%rdx
mov    %rcx,(%rax)
mov    %esi,0x8(%rax)
movss  %xmm0,0xc(%rax)
cmp    %r14,%rdx
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
subq   $0x1,0x18(%rsp)
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    %r12,%rdi
call   ADDR <benchmark::State::StartKeepRunning()>
mov    %r12,%rdi
call   ADDR <benchmark::State::FinishKeepRunning()>
cmpb   $0x0,0x18(%r12)
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    0x10(%rsp),%rcx
mov    0x10(%r12),%rax
pxor   %xmm4,%xmm4
sub    (%r12),%rax
add    0x8(%r12),%rax
imul   %rcx,%rax
cvtsi2sd %rax,%xmm4
movq   %xmm4,%rbx
lea    0x90(%rsp),%rbp
mov    $0x11,%edi
add    $0x40,%r12
mov    %rbp,0x80(%rsp)
call   ADDR <operator new(unsigned long)@plt>
movdqa 0x49839(%rip),%xmm0        # ADDR <_IO_stdin_used+OFF>
movb   $0x0,0x10(%rax)
mov    %r12,%rdi
lea    0x80(%rsp),%r13
mov    %r13,%rsi
mov    %rax,0x80(%rsp)
movups %xmm0,(%rax)
movq   $0x10,0x90(%rsp)
movq   $0x10,0x88(%rsp)
call   ADDR <std::map<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >, benchmark::Counter, std::less<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::pair<std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > const, benchmark::Counter> > >::operator[](std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> >&&)>
mov    0x80(%rsp),%rdi
mov    %rbx,(%rax)
movabs $0x3e800000001,%rcx
mov    %rcx,0x8(%rax)
cmp    %rbp,%rdi
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    0x90(%rsp),%rax
lea    0x1(%rax),%rsi
call   ADDR <operator delete(void*, unsigned long)@plt>
mov    0x60(%rsp),%rdi
test   %rdi,%rdi
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    0x70(%rsp),%rsi
sub    %rdi,%rsi
call   ADDR <operator delete(void*, unsigned long)@plt>
mov    0x40(%rsp),%rdi
test   %rdi,%rdi
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    0xa8(%rsp),%rax
sub    %fs:0x28,%rax
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    0x50(%rsp),%rsi
add    $0xb8,%rsp
pop    %rbx
pop    %rbp
sub    %rdi,%rsi
pop    %r12
pop    %r13
pop    %r14
pop    %r15
jmp    ADDR <operator delete(void*, unsigned long)@plt>
nopw   0x0(%rax,%rax,1)
mov    $0xfffffffffffffffe,%rdx
mov    %r14,%rsi
mov    %rbx,%rdi
call   ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)>
lea    0x10(%rbx),%rdx
cmp    %r14,%rdx
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    %rbp,0x20(%rsp)
mov    %r14,%rbp
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
nopl   0x0(%rax)
cmp    0x8(%rbx),%r15d
jae    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    %rdx,%rax
movss  0xc(%rdx),%xmm0
lea    0x10(%rdx),%r14
sub    %rbx,%rax
cmp    $0x10,%rax
jle    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    $0x10,%esi
movss  %xmm0,0xc(%rsp)
sub    %rax,%rsi
lea    (%rdx,%rsi,1),%rdi
mov    %rax,%rdx
mov    %rbx,%rsi
call   ADDR <memmove@plt>
movss  0xc(%rsp),%xmm0
mov    %r13,(%rbx)
mov    %r14,%rdx
mov    %r15d,0x8(%rbx)
movss  %xmm0,0xc(%rbx)
cmp    %rbp,%r14
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    (%rdx),%r13
mov    0x8(%rdx),%r15d
cmp    (%rbx),%r13
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
jl     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    %rdx,%rax
movss  0xc(%rdx),%xmm0
cmp    -0x10(%rax),%r13
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
cmp    -0x8(%rax),%r15d
jae    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
movdqu -0x10(%rax),%xmm3
sub    $0x10,%rax
movups %xmm3,0x10(%rax)
cmp    -0x10(%rax),%r13
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
jl     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
lea    0x10(%rdx),%r14
mov    %r13,(%rax)
mov    %r15d,0x8(%rax)
mov    %r14,%rdx
movss  %xmm0,0xc(%rax)
cmp    %rbp,%r14
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    0x20(%rsp),%rbp
subq   $0x1,0x18(%rsp)
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
nopl   0x0(%rax,%rax,1)
mov    0x10(%rsp),%rsi
mov    0x30(%rsp),%rdx
imul   %rbp,%rsi
shl    $0x4,%rsi
add    0x40(%rsp),%rsi
cmp    $0x10,%rdx
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    %rbx,%rdi
call   ADDR <memmove@plt>
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
xchg   %ax,%ax
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
movdqu (%rbx),%xmm6
movups %xmm6,(%rdx)
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
nopw   0x0(%rax,%rax,1)
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
movdqu (%rbx),%xmm5
movups %xmm5,0x0(%r13)
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
movq   $0x0,0x60(%rsp)
mov    0x1c(%r12),%eax
xor    %edx,%edx
movq   $0x0,0x70(%rsp)
movq   $0x0,0x30(%rsp)
mov    %rdx,0x68(%rsp)
test   %eax,%eax
je     ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    0xa8(%rsp),%rax
sub    %fs:0x28,%rax
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
add    $0xb8,%rsp
pop    %rbx
pop    %rbp
pop    %r12
pop    %r13
pop    %r14
pop    %r15
ret
xor    %ebx,%ebx
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
movdqu (%rsi),%xmm7
movups %xmm7,(%rbx)
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
mov    0xa8(%rsp),%rax
sub    %fs:0x28,%rax
jne    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&)+OFF>
lea    0x47796(%rip),%rdi        # ADDR <_IO_stdin_used+OFF>
call   ADDR <std::__throw_length_error(char const*)@plt>
call   ADDR <__stack_chk_fail@plt>
endbr64
mov    %rax,%rbx
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&) [clone .cold]>
endbr64
mov    %rax,%rbx
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&) [clone .cold]+OFF>
endbr64
mov    %rax,%rbx
jmp    ADDR <(anonymous namespace)::BM_SortFunctor(benchmark::State&) [clone .cold]+OFF>

<void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)>:
endbr64
push   %r15
mov    %rsi,%rax
push   %r14
sub    %rdi,%rax
push   %r13
push   %r12
push   %rbp
mov    %rdi,%rbp
push   %rbx
sub    $0x8,%rsp
cmp    $0x100,%rax
jle    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x26d>
mov    %rdx,%r14
mov    %rsi,%rdi
lea    0x10(%rbp),%r12
test   %rdx,%rdx
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x2d0>
sar    $0x5,%rax
mov    0x10(%rbp),%rdx
mov    -0x10(%rdi),%rsi
sub    $0x1,%r14
shl    $0x4,%rax
add    %rbp,%rax
mov    (%rax),%rcx
cmp    %rcx,%rdx
jne    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x120>
mov    0x18(%rbp),%r8d
mov    0x8(%rax),%r9d
cmp    %r9d,%r8d
jae    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x150>
cmp    %rsi,%rdx
jne    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x2c5>
mov    -0x8(%rdi),%edx
cmp    %edx,%r9d
jb     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x180>
cmp    %edx,%r8d
jb     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x291>
nopl   0x0(%rax)
mov    0x0(%rbp),%rdx
mov    0x8(%rbp),%rax
movdqu 0x10(%rbp),%xmm7
mov    %rdx,0x10(%rbp)
mov    %rax,0x18(%rbp)
movups %xmm7,0x0(%rbp)
mov    %rdi,%rsi
mov    %r12,%rbx
nop
mov    0x0(%rbp),%rdx
mov    (%rbx),%rcx
mov    %rbx,%r13
cmp    %rdx,%rcx
jne    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0xd7>
mov    0x8(%rbp),%eax
cmp    %eax,0x8(%rbx)
jae    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0xd9>
mov    0x10(%rbx),%rcx
add    $0x10,%rbx
mov    %rbx,%r13
cmp    %rdx,%rcx
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0xbf>
jl     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0xc7>
lea    -0x10(%rsi),%rax
mov    %rax,%rsi
cmp    (%rax),%rdx
jne    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0xfb>
mov    0x8(%rax),%r11d
cmp    %r11d,0x8(%rbp)
jae    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0xfd>
sub    $0x10,%rax
mov    %rax,%rsi
cmp    (%rax),%rdx
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0xe5>
jl     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0xef>
cmp    %rax,%rbx
jae    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x1a0>
mov    0x8(%rbx),%rdx
movdqu (%rax),%xmm2
add    $0x10,%rbx
movups %xmm2,-0x10(%rbx)
mov    %rcx,(%rax)
mov    %rdx,0x8(%rax)
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0xb0>
nop
jge    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x150>
cmp    %rsi,%rcx
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x2b7>
jl     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x180>
cmp    %rsi,%rdx
jne    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x57d>
mov    -0x8(%rdi),%edx
mov    0x18(%rbp),%r8d
cmp    %edx,%r8d
jb     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x291>
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x90>
nopl   0x0(%rax,%rax,1)
cmp    %rsi,%rdx
jne    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x27c>
mov    -0x8(%rdi),%ebx
cmp    %ebx,0x18(%rbp)
jb     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x90>
cmp    %rsi,%rcx
jne    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x28b>
mov    -0x8(%rdi),%esi
cmp    %esi,0x8(%rax)
jb     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x291>
nopw   0x0(%rax,%rax,1)
mov    0x0(%rbp),%rcx
mov    0x8(%rbp),%rdx
movdqu (%rax),%xmm7
movups %xmm7,0x0(%rbp)
mov    %rcx,(%rax)
mov    %rdx,0x8(%rax)
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0xa9>
nopl   0x0(%rax)
mov    %rdi,%rsi
mov    %r14,%rdx
mov    %rbx,%rdi
call   ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)>
mov    %rbx,%rax
sub    %rbp,%rax
cmp    $0x100,%rax
jle    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x26d>
test   %r14,%r14
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x2d3>
mov    %rbx,%rdi
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x3a>
nopl   0x0(%rax)
test   %rbx,%rbx
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x4d0>
lea    -0x1(%rcx),%rdx
mov    %rdx,%rsi
shr    $0x3f,%rsi
add    %rdx,%rsi
sar    $1,%rsi
test   %rcx,%rcx
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x590>
mov    %rsi,%rax
shl    $0x4,%rax
add    %rbp,%rax
cmp    %r8,(%rax)
jne    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x248>
cmp    %r11d,0x8(%rax)
jae    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x24a>
movdqu (%rax),%xmm4
shl    $0x4,%rcx
movups %xmm4,0x0(%rbp,%rcx,1)
lea    -0x1(%rsi),%rcx
mov    %rcx,%rdx
shr    $0x3f,%rdx
add    %rcx,%rdx
mov    %rsi,%rcx
sar    $1,%rdx
test   %rsi,%rsi
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x253>
mov    %rdx,%rsi
mov    %rsi,%rax
shl    $0x4,%rax
add    %rbp,%rax
cmp    %r8,(%rax)
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x20a>
jl     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x210>
shl    $0x4,%rcx
lea    0x0(%rbp,%rcx,1),%rax
mov    %r8,(%rax)
sub    $0x10,%r13
mov    %r11d,0x8(%rax)
movss  %xmm0,0xc(%rax)
cmp    $0x10,%r10
jg     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x420>
add    $0x8,%rsp
pop    %rbx
pop    %rbp
pop    %r12
pop    %r13
pop    %r14
pop    %r15
ret
jl     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x90>
cmp    %rsi,%rcx
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x16e>
jge    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x180>
mov    0x0(%rbp),%rdx
mov    0x8(%rbp),%eax
movss  0xc(%rbp),%xmm0
movdqu -0x10(%rdi),%xmm7
movups %xmm7,0x0(%rbp)
mov    %rdx,-0x10(%rdi)
mov    %eax,-0x8(%rdi)
movss  %xmm0,-0x4(%rdi)
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0xa9>
mov    -0x8(%rdi),%esi
cmp    %esi,0x8(%rax)
jb     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x180>
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x291>
jl     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x180>
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x90>
mov    %rsi,%r13
sar    $0x4,%rax
lea    -0x2(%rax),%r14
lea    -0x1(%rax),%r9
not    %rax
sar    $1,%r14
mov    %eax,%r8d
sar    $1,%r9
mov    %r14,%r11
and    $0x1,%r8d
mov    %r14,%r10
shl    $0x4,%r11
add    %rbp,%r11
nopl   0x0(%rax)
mov    (%r11),%rbx
mov    0x8(%r11),%r12d
mov    %r11,%rcx
movss  0xc(%r11),%xmm0
cmp    %r9,%r10
jge    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x374>
mov    %r10,%rsi
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x345>
nopw   0x0(%rax,%rax,1)
mov    0x8(%rcx),%r15d
cmp    %r15d,0x8(%rax)
cmovae %rax,%rcx
cmovae %rdi,%rdx
movdqu (%rcx),%xmm3
shl    $0x4,%rsi
movups %xmm3,0x0(%rbp,%rsi,1)
cmp    %r9,%rdx
jge    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x380>
mov    %rdx,%rsi
lea    0x1(%rsi),%rax
lea    (%rax,%rax,1),%rdi
shl    $0x5,%rax
lea    -0x1(%rdi),%rdx
add    %rbp,%rax
mov    %rdx,%rcx
mov    (%rax),%r15
shl    $0x4,%rcx
add    %rbp,%rcx
cmp    %r15,(%rcx)
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x320>
cmovle %rax,%rcx
cmovle %rdi,%rdx
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x330>
mov    %r10,%rdx
nopw   0x0(%rax,%rax,1)
cmp    %rdx,%r14
jne    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x38e>
test   %r8b,%r8b
jne    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x53c>
lea    -0x1(%rdx),%rsi
sar    $1,%rsi
cmp    %rdx,%r10
jge    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x56c>
mov    %rsi,%rax
shl    $0x4,%rax
add    %rbp,%rax
cmp    %rbx,(%rax)
jne    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x3f2>
cmp    %r12d,0x8(%rax)
jae    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x55d>
movdqu (%rax),%xmm5
lea    -0x1(%rsi),%rcx
shl    $0x4,%rdx
movups %xmm5,0x0(%rbp,%rdx,1)
mov    %rcx,%rdx
shr    $0x3f,%rdx
add    %rcx,%rdx
mov    %rdx,%rcx
mov    %rsi,%rdx
sar    $1,%rcx
cmp    %rsi,%r10
jge    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x3fd>
mov    %rcx,%rsi
mov    %rsi,%rax
shl    $0x4,%rax
add    %rbp,%rax
cmp    %rbx,(%rax)
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x3ad>
jl     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x3b7>
shl    $0x4,%rdx
lea    0x0(%rbp,%rdx,1),%rax
mov    %rbx,(%rax)
mov    %r12d,0x8(%rax)
movss  %xmm0,0xc(%rax)
test   %r10,%r10
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x41b>
sub    $0x1,%r10
sub    $0x10,%r11
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x300>
sub    $0x10,%r13
nop
mov    %r13,%r10
movdqu 0x0(%rbp),%xmm6
mov    0x0(%r13),%r8
sub    %rbp,%r10
mov    0x8(%r13),%r11d
movss  0xc(%r13),%xmm0
mov    %r10,%r9
movups %xmm6,0x0(%r13)
sar    $0x4,%r9
lea    -0x1(%r9),%rax
mov    %r9,%rbx
mov    %rax,%rdi
and    $0x1,%ebx
shr    $0x3f,%rdi
add    %rax,%rdi
sar    $1,%rdi
cmp    $0x20,%r10
jle    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x52f>
xor    %esi,%esi
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x499>
nopw   0x0(%rax,%rax,1)
mov    0x8(%rax),%r15d
cmp    %r15d,0x8(%rdx)
cmovae %rdx,%rax
cmovae %r12,%rcx
movdqu (%rax),%xmm1
shl    $0x4,%rsi
movups %xmm1,0x0(%rbp,%rsi,1)
cmp    %rdi,%rcx
jge    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x1d8>
mov    %rcx,%rsi
lea    0x1(%rsi),%rdx
lea    (%rdx,%rdx,1),%r12
shl    $0x5,%rdx
lea    -0x1(%r12),%rcx
add    %rbp,%rdx
mov    %rcx,%rax
mov    (%rdx),%r14
shl    $0x4,%rax
add    %rbp,%rax
cmp    %r14,(%rax)
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x470>
cmovle %rdx,%rax
cmovle %r12,%rcx
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x480>
nopl   0x0(%rax)
sub    $0x2,%r9
sar    $1,%r9
cmp    %r9,%rcx
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x50f>
lea    -0x1(%rcx),%rdx
mov    %rdx,%rsi
shr    $0x3f,%rsi
add    %rdx,%rsi
sar    $1,%rsi
test   %rcx,%rcx
jne    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x1fb>
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x253>
nopl   0x0(%rax,%rax,1)
cmp    $0x2,%rax
mov    %rbp,%rax
ja     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x253>
xor    %ecx,%ecx
lea    0x1(%rcx,%rcx,1),%rdx
mov    %rdx,%rsi
shl    $0x4,%rsi
movdqu 0x0(%rbp,%rsi,1),%xmm7
mov    %rcx,%rsi
mov    %rdx,%rcx
movups %xmm7,(%rax)
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x1fb>
test   %rbx,%rbx
je     ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x500>
mov    %rbp,%rax
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x253>
lea    (%rdx,%rdx,1),%rsi
lea    0x1(%rsi),%rdx
mov    %rdx,%rax
shl    $0x4,%rax
add    %rbp,%rax
movdqu (%rax),%xmm6
movups %xmm6,(%rcx)
mov    %rax,%rcx
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x392>
mov    %rdx,%rax
shl    $0x4,%rax
add    %rbp,%rax
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x3fd>
mov    %rbx,(%rcx)
mov    %r12d,0x8(%rcx)
movss  %xmm0,0xc(%rcx)
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x40e>
jge    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x90>
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x291>
nopl   0x0(%rax,%rax,1)
mov    %r8,(%rax)
sub    $0x10,%r13
mov    %r11d,0x8(%rax)
movss  %xmm0,0xc(%rax)
jmp    ADDR <void std::__introsort_loop<__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder> >(__gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, __gnu_cxx::__normal_iterator<minidaq::Single*, std::vector<minidaq::Single, std::allocator<minidaq::Single> > >, long, __gnu_cxx::__ops::_Iter_comp_iter<minidaq::TimeOrder>)+0x420>
cs nopw 0x0(%rax,%rax,1)
nop

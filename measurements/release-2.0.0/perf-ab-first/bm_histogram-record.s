:
	mov    $0x8000,%esi
	mov    %r12,%rdi
	call   
	mov    0x20(%rsp),%rdi
	test   %rdi,%rdi
	je     
	call   
	mov    0xa18(%rsp),%rax
	sub    %fs:0x28,%rax
	jne    
	mov    %rbx,%rdi
	call   
	call   
	lea    0xceb(%rip),%rax        # 
	mov    %rbp,%rdi
	mov    %r12,0x0(%rbp)
	mov    %rax,0xe0(%rbp)
	call   
	mov    %rbx,%rdi
	call   , std::allocator<char> >::_M_dispose()>
	mov    $0xe8,%edi
	call   
	mov    %r13,%rdx
	lea    0x462d2(%rip),%rsi        # 
	mov    %rbx,%rdi
	mov    %rax,%rbp
	call   , std::allocator<char> >::basic_string<std::allocator<char> >(char const*, std::allocator<char> const&)>
	mov    %rbx,%rsi
	mov    %rbp,%rdi
	call   , std::allocator<char> > const&)>
	lea    0x93f(%rip),%rax        # 
	mov    %r12,0x0(%rbp)
	mov    %rbp,%rdi
	mov    %rax,0xe0(%rbp)
	call   
	mov    %rbx,%rdi
	call   , std::allocator<char> >::_M_dispose()>
	mov    $0xe8,%edi
	call   
	mov    %r13,%rdx
	lea    0x46298(%rip),%rsi        # 
	mov    %rbx,%rdi
	mov    %rax,%rbp
	call   , std::allocator<char> >::basic_string<std::allocator<char> >(char const*, std::allocator<char> const&)>
	mov    %rbx,%rsi
	mov    %rbp,%rdi
	call   , std::allocator<char> > const&)>
	lea    0x953(%rip),%rax        # 
	mov    %r12,0x0(%rbp)
	mov    %rbp,%rdi
	mov    %rax,0xe0(%rbp)
	call   
	mov    %rax,%rdi
	mov    $0x1,%esi
	call   
	mov    %rbx,%rdi
	call   , std::allocator<char> >::_M_dispose()>
	mov    0x38(%rsp),%rax
	sub    %fs:0x28,%rax
	jne    
	add    $0x48,%rsp
	pop    %rbx
	pop    %rbp
	pop    %r12
	pop    %r13
	ret
	call   
	endbr64
	mov    %rax,%r12
	jmp    
	endbr64
	mov    %rax,%r12
	jmp    
	endbr64
	mov    %rax,%r12
	jmp    
	endbr64
	mov    %rax,%r12
	jmp    
	endbr64
	mov    %rax,%r12
	jmp    
	endbr64
	mov    %rax,%r12
	jmp    
	endbr64
	mov    %rax,%r12
	jmp    
	endbr64
	mov    %rax,%r12
	jmp    
	endbr64
	mov    %rax,%r12
	jmp    
	endbr64
	mov    %rax,%r12
	jmp    
	nopl   (%rax)
	call   
	sub    $0x1,%r12d
	jne    
	mov    0x1c(%rbp),%eax
	test   %eax,%eax
	je     
	mov    %rbp,%rdi
	call   
	mov    %rbp,%rdi
	call   
	mov    0x20(%rsp),%rdi
	test   %rdi,%rdi
	je     
	call   
	mov    0xa18(%rsp),%rax
	sub    %fs:0x28,%rax
	jne    
	add    $0xa28,%rsp
	pop    %rbx
	pop    %rbp
	pop    %r12
	pop    %r13
	ret
	mov    %rbp,%rdi
	mov    0x10(%rbp),%rbx
	call   
	test   %rbx,%rbx
	je     
	movsd  0x4656f(%rip),%xmm7        # 
	movsd  0x4656f(%rip),%xmm6        # 
	mov    %rbx,%rsi
	mov    $0x1,%edi
	movsd  0x46567(%rip),%xmm5        # 
	movsd  0x46577(%rip),%xmm4        # 
	movabs $0x8000000000000000,%r8
	movsd  0x4655d(%rip),%xmm3        # 
	movsd  0x4654c(%rip),%xmm8        # 
	nopl   0x0(%rax)
	mov    0x28(%rsp),%rcx
	xor    %eax,%eax
	test   %rcx,%rcx
	je     
	js     
	pxor   %xmm0,%xmm0
	cvtsi2sd %rcx,%xmm0
	mulsd  %xmm7,%xmm0
	subsd  %xmm6,%xmm0
	movapd %xmm0,%xmm1
	andpd  %xmm4,%xmm1
	ucomisd %xmm1,%xmm5
	jbe    
	cvttsd2si %xmm0,%rax
	pxor   %xmm1,%xmm1
	movapd %xmm0,%xmm2
	cvtsi2sd %rax,%xmm1
	cmpnlesd %xmm1,%xmm2
	andpd  %xmm8,%xmm2
	addsd  %xmm2,%xmm1
	movapd %xmm4,%xmm2
	andnpd %xmm0,%xmm2
	orpd   %xmm2,%xmm1
	movapd %xmm1,%xmm0
	comisd %xmm3,%xmm0
	jae    
	cvttsd2si %xmm0,%rax
	cmp    %rax,%rcx
	cmova  %rax,%rcx
	test   %rax,%rax
	cmove  %rdi,%rcx
	cmpq   $0x0,0x18(%rsp)
	je     
	mov    0x20(%rsp),%r10
	xor    %edx,%edx
	xor    %eax,%eax
	jmp    
	nopl   0x0(%rax)
	add    $0x1,%rax
	cmp    0x18(%rsp),%rax
	jae    
	mov    (%r10,%rax,8),%r9
	add    %r9,%rdx
	cmp    %rcx,%rdx
	jb     
	mov    0x48(%rsp),%r9
	mov    0x8(%rsp),%rcx
	lea    (%rcx,%rcx,1),%rdx
	cmp    %rdx,%rax
	jb     
	xor    %edx,%edx
	div    %rcx
	lea    0x1(%rcx,%rdx,1),%rdx
	lea    -0x1(%rax),%ecx
	shl    %cl,%rdx
	lea    -0x1(%rdx),%rax
	cmp    %rax,%r9
	cmovbe %r9,%rax
	sub    $0x1,%rsi
	jne    
	jmp    
	nopl   0x0(%rax,%rax,1)
	subsd  %xmm3,%xmm0
	cvttsd2si %xmm0,%rax
	xor    %r8,%rax
	jmp    
	nopl   0x0(%rax)
	mov    %rcx,%rax
	mov    %rcx,%rdx
	pxor   %xmm0,%xmm0
	shr    $1,%rax
	and    $0x1,%edx
	or     %rdx,%rax
	cvtsi2sd %rax,%xmm0
	addsd  %xmm0,%xmm0
	jmp    
	nopl   0x0(%rax)
	mov    0x48(%rsp),%rax
	jmp    
	call   
	endbr64
	mov    %rax,%rbx
	jmp    
	nopl   0x0(%rax,%rax,1)
:
	endbr64
	push   %r14
	push   %r13
	push   %r12
	push   %rbp
	mov    %rdi,%rbp
	mov    $0x8808,%edi
	push   %rbx
	sub    $0xa20,%rsp
	movdqa 0x4623d(%rip),%xmm0        # 
	mov    %fs:0x28,%rax
	mov    %rax,0xa18(%rsp)
	xor    %eax,%eax
	movl   $0x7,(%rsp)
	lea    0x50(%rsp),%rbx
	movups %xmm0,0x8(%rsp)
	movq   $0x1101,0x18(%rsp)
	call   
	mov    $0x8808,%edx
	xor    %esi,%esi
	mov    %rax,%rdi
	call   
	pxor   %xmm0,%xmm0
	mov    $0x1,%ecx
	movq   $0x0,0x48(%rsp)
	movups %xmm0,0x28(%rsp)
	movdqa 0x461ed(%rip),%xmm0        # 
	mov    $0x1,%edx
	movabs $0x5851f42d4c957f2d,%rsi
	mov    %rax,0x20(%rsp)
	movq   $0x1,0x50(%rsp)
	movups %xmm0,0x38(%rsp)
	nopl   (%rax)
	mov    %rcx,%rax
	shr    $0x3e,%rax
	xor    %rcx,%rax
	imul   %rsi,%rax
	lea    (%rdx,%rax,1),%rcx
	mov    %rcx,(%rbx,%rdx,8)
	add    $0x1,%rdx
	cmp    $0x138,%rdx
	jne    
	mov    $0x8000,%edi
	movq   $0x138,0xa10(%rsp)
	call   
	movq   $0x0,(%rax)
	mov    %rax,%r12
	lea    0x8(%rax),%rdi
	xor    %esi,%esi
	mov    $0x7ff8,%edx
	mov    %r12,%r13
	lea    0x8000(%r12),%r14
	call   
	cs nopw 0x0(%rax,%rax,1)
	mov    %rbx,%rdi
	add    $0x8,%r13
	call   ::operator()()>
	shr    $0x28,%rax
	mov    %rax,-0x8(%r13)
	cmp    %r13,%r14
	jne    
	mov    0x1c(%rbp),%eax
	test   %eax,%eax
	jne    
	mov    %rbp,%rdi
	mov    0x10(%rbp),%r13
	call   
	test   %r13,%r13
	je     
	xor    %ebx,%ebx
	mov    %rsp,%r14
	nopw   0x0(%rax,%rax,1)
	mov    %rbx,%rax
	mov    %r14,%rdi
	add    $0x1,%rbx
	and    $0xfff,%eax
	mov    (%r12,%rax,8),%rsi
	call   
	cmp    %r13,%rbx
	jne    
	mov    %rbp,%rdi
	call   
	mov    0x28(%rsp),%rax
	mov    $0x8000,%esi
	mov    %r12,%rdi
	call   
	mov    0x20(%rsp),%rdi
	test   %rdi,%rdi
	je     
	call   
	mov    0xa18(%rsp),%rax
	sub    %fs:0x28,%rax
	jne    
	add    $0xa20,%rsp
	pop    %rbx
	pop    %rbp
	pop    %r12
	pop    %r13
	pop    %r14
	ret
	mov    %rbp,%rdi
	call   
	jmp    
	call   
	endbr64
	mov    %rax,%rbx
	jmp    
	endbr64
	mov    %rax,%rbx
	jmp    
:
	endbr64
	xor    %edx,%edx
	test   %rsi,%rsi
	mov    %rdi,%rax
	cmovns %rsi,%rdx
	cmp    %rdx,0x10(%rdi)
	jb     
	mov    0x8(%rax),%rdi
	mov    (%rax),%r8d
	mov    %rdx,%rcx
	lea    (%rdi,%rdi,1),%rsi
	cmp    %rsi,%rdx
	jb     
	xor    %esi,%esi
	test   %rdx,%rdx
	je     
	bsr    %rdx,%rcx
	lea    0x1(%rcx),%esi
	sub    %r8d,%esi
	mov    %rdx,%r9
	lea    -0x1(%rsi),%ecx
	imul   %rdi,%rsi
	shr    %cl,%r9
	mov    %r9,%rcx
	add    %rsi,%rcx
	sub    %rdi,%rcx
	mov    0x20(%rax),%rsi
	lea    (%rsi,%rcx,8),%rsi
	mov    (%rsi),%rcx
	add    $0x1,%rcx
	mov    %rcx,(%rsi)
	mov    0x28(%rax),%rcx
	add    $0x1,%rcx
	mov    %rcx,0x28(%rax)
	mov    0x38(%rax),%rcx
	add    %rdx,%rcx
	mov    %rcx,0x38(%rax)
	mov    0x40(%rax),%rcx
	cmp    %rcx,%rdx
	jb     
	mov    0x48(%rax),%rcx
	cmp    %rdx,%rcx
	jb     
	ret
	mov    %rdx,0x48(%rax)
	ret
	nopl   (%rax)
	mov    %rdx,0x40(%rax)
	jmp    
	xchg   %ax,%ax
	mov    0x30(%rdi),%rdx
	add    $0x1,%rdx
	mov    %rdx,0x30(%rdi)
	mov    0x10(%rdi),%rdx
	jmp    
	cs nopw 0x0(%rax,%rax,1)
	nop

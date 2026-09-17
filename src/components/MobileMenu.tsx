import { Menu, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

type MenuLink = { href: string; label: string };

export default function MobileMenu({ links }: { links: MenuLink[] }) {
	const [open, setOpen] = useState(false);
	const firstLinkRef = useRef<HTMLAnchorElement>(null);

	useEffect(() => {
		if (open) firstLinkRef.current?.focus();
	}, [open]);

	useEffect(() => {
		const onKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Escape') setOpen(false);
		};
		window.addEventListener('keydown', onKeyDown);
		return () => window.removeEventListener('keydown', onKeyDown);
	}, []);

	return (
		<div className="mobile-menu">
			<button className="icon-button mobile-menu__toggle" type="button" aria-label={open ? '关闭菜单' : '打开菜单'} aria-expanded={open} aria-controls="mobile-navigation" onClick={() => setOpen((current) => !current)}>
				{open ? <X size={20} strokeWidth={1.8} aria-hidden="true" /> : <Menu size={20} strokeWidth={1.8} aria-hidden="true" />}
			</button>
			{open && (
				<nav id="mobile-navigation" className="mobile-menu__panel" aria-label="移动端主导航">
					{links.map((link, index) => (
						<a ref={index === 0 ? firstLinkRef : undefined} href={link.href} onClick={() => setOpen(false)}>{link.label}</a>
					))}
					<a className="mobile-menu__agent" href="/#agent" onClick={() => setOpen(false)}>和我的 Agent 聊聊 <span aria-hidden="true">↗</span></a>
				</nav>
			)}
		</div>
	);
}

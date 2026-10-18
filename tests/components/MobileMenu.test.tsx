import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import MobileMenu from '@/components/MobileMenu';

describe('MobileMenu', () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('renders mapped navigation links without a React key warning', async () => {
		const user = userEvent.setup();
		const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
		render(<MobileMenu links={[{ href: '/', label: '首页' }]} />);

		await user.click(screen.getByRole('button', { name: '打开菜单' }));

		expect(screen.getByRole('navigation', { name: '移动端主导航' })).toBeVisible();
		expect(consoleError.mock.calls.flat().join(' ')).not.toContain('Each child in a list should have a unique "key" prop.');
	});
});

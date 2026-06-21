const { test, expect } = require('@playwright/test')

test.describe('登录和菜单导航', () => {
  test('登录成功后可以正常切换菜单', async ({ page }) => {
    // 1. 打开登录页
    await page.goto('http://localhost:5173/login')
    await expect(page).toHaveURL(/\/login$/)

    // 2. 输入账号密码
    await page.fill('input[placeholder="用户名"]', 'admin')
    await page.fill('input[placeholder="密码"]', 'admin123')

    // 3. 点击登录
    await page.click('button:has-text("登 录")')

    // 4. 等待跳转到 dashboard
    await page.waitForURL('http://localhost:5173/dashboard', { timeout: 5000 })
    await expect(page).toHaveURL('http://localhost:5173/dashboard')

    // 5. 验证 localStorage 中有 token
    const token = await page.evaluate(() => localStorage.getItem('token'))
    expect(token).toBeTruthy()
    console.log('Token exists:', token.substring(0, 30) + '...')

    // 6. 使用 Vue Router 编程式导航到食材管理
    await page.evaluate(() => {
      const app = document.querySelector('#app')
      if (app && app.__vue_app__) {
        const router = app.__vue_app__.config.globalProperties.$router
        if (router) {
          router.push('/ingredients')
        }
      }
    })

    // 7. 等待页面加载（等待食材表格出现）
    await page.waitForSelector('.el-table', { timeout: 5000 })

    // 8. 检查当前 URL 和 localStorage
    const currentUrl = page.url()
    const tokenAfterNav = await page.evaluate(() => localStorage.getItem('token'))
    console.log('Current URL after nav:', currentUrl)
    console.log('Token after nav:', tokenAfterNav ? tokenAfterNav.substring(0, 30) + '...' : 'NULL')

    // 9. 验证页面没有被跳回登录页
    expect(currentUrl).not.toContain('/login')

    // 10. 验证 localStorage 仍然有效
    expect(tokenAfterNav).toBeTruthy()
    expect(tokenAfterNav).toBe(token)

    // 11. 验证页面内容加载成功
    await expect(page.locator('.el-card__header:has-text("食材管理")')).toBeVisible()
    await expect(page.locator('button:has-text("添加食材")')).toBeVisible()

    // 12. 验证表格数据加载成功
    const tableRows = await page.locator('.el-table__row').count()
    console.log('Table rows:', tableRows)
    expect(tableRows).toBeGreaterThan(0)

    // 13. 继续测试其他页面导航
    await page.evaluate(() => {
      const app = document.querySelector('#app')
      if (app && app.__vue_app__) {
        const router = app.__vue_app__.config.globalProperties.$router
        if (router) router.push('/suppliers')
      }
    })
    await page.waitForSelector('.el-table', { timeout: 5000 })
    expect(page.url()).not.toContain('/login')
    console.log('Current URL after suppliers nav:', page.url())

    // 14. 测试教育局监管
    await page.evaluate(() => {
      const app = document.querySelector('#app')
      if (app && app.__vue_app__) {
        const router = app.__vue_app__.config.globalProperties.$router
        if (router) router.push('/gov')
      }
    })
    await page.waitForTimeout(2000)
    expect(page.url()).not.toContain('/login')
    console.log('Current URL after gov nav:', page.url())

    // 15. 最终验证 token 仍然有效
    const finalToken = await page.evaluate(() => localStorage.getItem('token'))
    expect(finalToken).toBeTruthy()
    expect(finalToken).toBe(token)
    console.log('Final token preserved:', finalToken.substring(0, 30) + '...')
  })

  test('直接访问受保护路由会被重定向到登录页', async ({ page }) => {
    // 清除 localStorage
    await page.goto('http://localhost:5173/login')
    await page.evaluate(() => localStorage.clear())

    // 直接访问 dashboard
    await page.goto('http://localhost:5173/dashboard')

    // 应该被重定向到登录页
    await page.waitForURL(/\/login$/, { timeout: 5000 })
    await expect(page).toHaveURL(/\/login$/)
  })
})

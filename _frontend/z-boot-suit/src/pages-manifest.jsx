import { HomeOutlined, MonitorOutlined } from '@ant-design/icons'
import HomePage from './HomePage'
import StatusPage from './StatusPage'

/** 菜单 + 路由清单（lead 008 §10/§14/§16 批量落地，suit 内联形态）。 */
export const appMeta = { title: 'boot 服务台', short: 'z-boot' }

export const menuItems = [
    { key: '/z-boot/home', label: '首页', icon: <HomeOutlined /> },
    { key: '/z-boot/status', label: '服务状态', icon: <MonitorOutlined /> },
]

export const routeTable = [
    { path: '/z-boot/home', Component: HomePage },
    { path: '/z-boot/status', Component: StatusPage },
]

export { default as HomePage } from './HomePage'
export { default as LoginPage } from './LoginPage'

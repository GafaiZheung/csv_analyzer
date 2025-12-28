"""
SVG图标管理模块 - 统一管理所有图标
"""

from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QByteArray, QSize, QRectF
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication

from csv_analyzer.frontend.styles.theme import VSCODE_COLORS


class IconManager:
    """图标管理器"""
    
    # 缓存已创建的图标
    _cache: dict = {}
    
    # SVG图标定义
    ICONS = {
        # 文件操作
        "folder_open": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
        """,
        "file": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
            </svg>
        """,
        "save": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                <polyline points="17 21 17 13 7 13 7 21"/>
                <polyline points="7 3 7 8 15 8"/>
            </svg>
        """,
        "export": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
        """,
        
        # 表格和数据
        "table": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="3" y1="15" x2="21" y2="15"/>
                <line x1="9" y1="3" x2="9" y2="21"/>
                <line x1="15" y1="3" x2="15" y2="21"/>
            </svg>
        """,
        "column": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <line x1="9" y1="3" x2="9" y2="21"/>
            </svg>
        """,
        "view": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
            </svg>
        """,
        
        # 操作
        "play": """
            <svg viewBox="0 0 24 24" fill="{color}" stroke="none">
                <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
        """,
        "refresh": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <polyline points="23 4 23 10 17 10"/>
                <polyline points="1 20 1 14 7 14"/>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
            </svg>
        """,
        "trash": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
        """,
        "clear": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
        """,
        "format": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <line x1="21" y1="10" x2="3" y2="10"/>
                <line x1="21" y1="6" x2="3" y2="6"/>
                <line x1="21" y1="14" x2="3" y2="14"/>
                <line x1="21" y1="18" x2="3" y2="18"/>
            </svg>
        """,
        
        # 排序
        "sort_asc": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <line x1="12" y1="19" x2="12" y2="5"/>
                <polyline points="5 12 12 5 19 12"/>
            </svg>
        """,
        "sort_desc": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <polyline points="19 12 12 19 5 12"/>
            </svg>
        """,
        
        # 导航
        "chevron_right": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <polyline points="9 18 15 12 9 6"/>
            </svg>
        """,
        "chevron_down": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <polyline points="6 9 12 15 18 9"/>
            </svg>
        """,
        "first": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <polyline points="11 17 6 12 11 7"/>
                <polyline points="18 17 13 12 18 7"/>
            </svg>
        """,
        "last": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <polyline points="13 17 18 12 13 7"/>
                <polyline points="6 17 11 12 6 7"/>
            </svg>
        """,
        "prev": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <polyline points="15 18 9 12 15 6"/>
            </svg>
        """,
        "next": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <polyline points="9 18 15 12 9 6"/>
            </svg>
        """,
        
        # 分析
        "chart": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <line x1="18" y1="20" x2="18" y2="10"/>
                <line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/>
            </svg>
        """,
        "stats": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <path d="M21.21 15.89A10 10 0 1 1 8 2.83"/>
                <path d="M22 12A10 10 0 0 0 12 2v10z"/>
            </svg>
        """,
        "search": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
        """,
        "filter": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
            </svg>
        """,
        
        # 数据类型
        "number": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <text x="6" y="17" font-size="14" font-family="monospace" fill="{color}" stroke="none">123</text>
            </svg>
        """,
        "text": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <polyline points="4 7 4 4 20 4 20 7"/>
                <line x1="9" y1="20" x2="15" y2="20"/>
                <line x1="12" y1="4" x2="12" y2="20"/>
            </svg>
        """,
        "calendar": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
        """,
        
        # 状态
        "check": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
            </svg>
        """,
        "warning": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
        """,
        "info": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="16" x2="12" y2="12"/>
                <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
        """,
        "error": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
        """,
        
        # 其他
        "plus": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
        """,
        "minus": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
        """,
        "more": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <circle cx="12" cy="12" r="1"/>
                <circle cx="19" cy="12" r="1"/>
                <circle cx="5" cy="12" r="1"/>
            </svg>
        """,
        "settings": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
        """,
        "database": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <ellipse cx="12" cy="5" rx="9" ry="3"/>
                <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
                <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
            </svg>
        """,
        "code": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <polyline points="16 18 22 12 16 6"/>
                <polyline points="8 6 2 12 8 18"/>
            </svg>
        """,
        "null": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
            </svg>
        """,
        "distinct": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"/>
                <rect x="14" y="3" width="7" height="7"/>
                <rect x="14" y="14" width="7" height="7"/>
                <rect x="3" y="14" width="7" height="7"/>
            </svg>
        """,
        "count": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <text x="4" y="17" font-size="12" font-family="monospace" fill="{color}" stroke="none">#</text>
                <line x1="14" y1="6" x2="20" y2="6"/>
                <line x1="14" y1="12" x2="20" y2="12"/>
                <line x1="14" y1="18" x2="20" y2="18"/>
            </svg>
        """,
        "group": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="3" y1="15" x2="21" y2="15"/>
            </svg>
        """,
        
        # 面板切换图标
        "panel_left": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <line x1="9" y1="3" x2="9" y2="21"/>
            </svg>
        """,
        "panel_right": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <line x1="15" y1="3" x2="15" y2="21"/>
            </svg>
        """,
        "panel_bottom": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <line x1="3" y1="15" x2="21" y2="15"/>
            </svg>
        """,
        "layout": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="9" y1="21" x2="9" y2="9"/>
            </svg>
        """,
        "folder": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
        """,
        "workspace": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                <line x1="12" y1="11" x2="12" y2="17"/>
                <line x1="9" y1="14" x2="15" y2="14"/>
            </svg>
        """,
        "cell": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <rect x="7" y="7" width="10" height="10" fill="{color}" opacity="0.3"/>
            </svg>
        """,
        "inspect": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                <line x1="11" y1="8" x2="11" y2="14"/>
                <line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
        """,

        # 窗口控制（无边框标题栏用）
        "window_minimize": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round">
                <line x1="6" y1="18" x2="18" y2="18"/>
            </svg>
        """,
        "window_maximize": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round">
                <rect x="6" y="6" width="12" height="12" rx="1"/>
            </svg>
        """,
        "window_restore": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round">
                <rect x="7" y="9" width="10" height="10" rx="1"/>
                <path d="M9 9V7a1 1 0 0 1 1-1h7a1 1 0 0 1 1 1v7h-2"/>
            </svg>
        """,
        "window_close": """
            <svg viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round">
                <line x1="7" y1="7" x2="17" y2="17"/>
                <line x1="17" y1="7" x2="7" y2="17"/>
            </svg>
        """,
    }
    
    @classmethod
    def get_icon(cls, name: str, color: str = None, size: int = 16) -> QIcon:
        """
        获取图标
        
        Args:
            name: 图标名称
            color: 图标颜色，默认使用主题前景色
            size: 图标尺寸
            
        Returns:
            QIcon: 图标对象
        """
        if color is None:
            color = VSCODE_COLORS['foreground']
        
        # 设备像素比会影响清晰度，需纳入缓存键
        dpr = 1.0
        try:
            app = QApplication.instance()
            if app and app.primaryScreen():
                dpr = float(app.primaryScreen().devicePixelRatio() or 1.0)
        except Exception:
            dpr = 1.0

        cache_key = f"{name}_{color}_{size}_{int(dpr * 100)}"
        
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        svg_template = cls.ICONS.get(name)
        if not svg_template:
            # 返回空图标
            return QIcon()
        
        # 替换颜色
        svg_data = svg_template.format(color=color).strip()

        # 确保 SVG 命名空间和尺寸存在，避免部分平台渲染尺寸异常或只绘制左上角
        if svg_data.startswith("<svg"):
            first_tag = svg_data.split(">", 1)[0]
            needs_xmlns = "xmlns=" not in first_tag
            needs_width = "width=" not in first_tag
            needs_height = "height=" not in first_tag
            needs_par = "preserveAspectRatio=" not in first_tag

            attrs = []
            if needs_xmlns:
                attrs.append('xmlns="http://www.w3.org/2000/svg"')
            if needs_width:
                attrs.append('width="24"')
            if needs_height:
                attrs.append('height="24"')
            if needs_par:
                attrs.append('preserveAspectRatio="xMidYMid meet"')

            if attrs:
                svg_data = svg_data.replace(
                    "<svg",
                    "<svg " + " ".join(attrs),
                    1,
                )
        
        # 创建QIcon
        icon = cls._svg_to_icon(svg_data, size, dpr)
        cls._cache[cache_key] = icon
        
        return icon
    
    @classmethod
    def _svg_to_icon(cls, svg_data: str, size: int, dpr: float) -> QIcon:
        """将SVG数据转换为QIcon（高DPI清晰，且不裁切）"""
        # 用高分辨率 pixmap 渲染，再通过 devicePixelRatio 映射回逻辑尺寸
        dpr = max(1.0, float(dpr or 1.0))
        device_w = max(1, int(round(size * dpr)))
        device_h = max(1, int(round(size * dpr)))

        renderer = QSvgRenderer(QByteArray(svg_data.encode()))

        pixmap = QPixmap(device_w, device_h)
        pixmap.fill(Qt.GlobalColor.transparent)
        pixmap.setDevicePixelRatio(dpr)

        # 关键点：渲染目标矩形要用“逻辑尺寸”(size x size)，否则会出现只显示左上角/裁切
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(painter, QRectF(0, 0, float(size), float(size)))
        painter.end()

        return QIcon(pixmap)
    
    @classmethod
    def get_pixmap(cls, name: str, color: str = None, size: int = 16) -> QPixmap:
        """获取Pixmap"""
        icon = cls.get_icon(name, color, size)
        return icon.pixmap(QSize(size, size))


# 便捷函数
def get_icon(name: str, color: str = None, size: int = 16) -> QIcon:
    """获取图标的便捷函数"""
    return IconManager.get_icon(name, color, size)

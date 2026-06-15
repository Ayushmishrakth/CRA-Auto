"""
Chart Generator - CRITICAL: matplotlib.use('Agg') MUST be first 3 lines
Renders all charts to BytesIO PNG - no temp files, no disk writes, pure memory.
All colors converted to 0-1 RGB range for compatibility.
"""
import io
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import logging

logger = logging.getLogger(__name__)

# Brand Colors (hex format)
COLORS_HEX = {
    'critical': '#DC2626',
    'high': '#EA580C',
    'medium': '#D97706',
    'low': '#65A30D',
    'info': '#2563EB',
}

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple (0-1 range) for matplotlib."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

# Pre-convert all colors to 0-1 RGB range
COLORS = {k: hex_to_rgb(v) for k, v in COLORS_HEX.items()}


def _save_to_bytes(fig):
    """Save matplotlib figure to BytesIO, close figure, return bytes."""
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        buf.seek(0)
    finally:
        plt.close(fig)
    return buf


def generate_severity_pie_chart(severity_data: dict) -> io.BytesIO:
    """Donut chart: severity distribution."""
    try:
        labels = []
        sizes = []
        colors_list = []
        order = ['critical', 'high', 'medium', 'low', 'info']

        for sev in order:
            count = severity_data.get(sev, 0)
            if count > 0:
                labels.append(f"{sev.capitalize()} ({count})")
                sizes.append(count)
                # COLORS dict now contains 0-1 RGB tuples
                colors_list.append(COLORS[sev])

        if not sizes:
            sizes = [1]
            labels = ['No Data']
            colors_list = [(0.88, 0.88, 0.88)]  # Gray in 0-1 RGB

        fig, ax = plt.subplots(figsize=(5, 3.5), facecolor='white')
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors_list, autopct='%1.1f%%',
            startangle=90, pctdistance=0.85,
            wedgeprops=dict(width=0.6, edgecolor='white', linewidth=2)
        )

        for text in texts:
            text.set_fontsize(8)
            text.set_fontweight('bold')
        for autotext in autotexts:
            autotext.set_fontsize(8)
            autotext.set_color('white')
            autotext.set_fontweight('bold')

        return _save_to_bytes(fig)
    except Exception as e:
        logger.error(f"Severity pie chart error: {e}", exc_info=True)
        raise


def generate_pass_fail_chart(pass_count: int, fail_count: int) -> io.BytesIO:
    """Horizontal bar chart: pass vs fail."""
    try:
        fig, ax = plt.subplots(figsize=(5.5, 2.5), facecolor='white')
        ax.set_facecolor((0.973, 0.98, 0.992))  # #F8FAFC in 0-1 RGB

        categories = ['Pass', 'Fail']
        values = [pass_count, fail_count]
        # Convert hex colors to 0-1 RGB
        bar_colors = [(0.087, 0.639, 0.29), (0.862, 0.149, 0.149)]  # Green, Red

        bars = ax.barh(categories, values, color=bar_colors, height=0.4, edgecolor='white', linewidth=1)

        max_val = max(values) if values else 1
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max_val * 0.02, bar.get_y() + bar.get_height()/2,
                   str(val), ha='left', va='center', fontsize=10, fontweight='bold',
                   color=(0.122, 0.227, 0.373))  # Dark blue in 0-1 RGB

        ax.set_xlabel('Count', fontsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_xlim(0, max_val * 1.15 if values else 1)

        return _save_to_bytes(fig)
    except Exception as e:
        logger.error(f"Pass/Fail chart error: {e}", exc_info=True)
        raise


def generate_service_chart(service_data: dict) -> io.BytesIO:
    """Stacked horizontal bar chart: pass/fail per service."""
    try:
        if not service_data:
            service_data = {'No Data': {'pass': 0, 'fail': 0}}

        services = sorted(service_data.keys())
        pass_vals = [service_data[s].get('pass', 0) for s in services]
        fail_vals = [service_data[s].get('fail', 0) for s in services]

        fig_h = max(3.5, len(services) * 0.35)
        fig, ax = plt.subplots(figsize=(6, fig_h), facecolor='white')
        ax.set_facecolor((0.973, 0.98, 0.992))  # #F8FAFC in 0-1 RGB

        y_pos = list(range(len(services)))
        # Use 0-1 RGB values for colors
        ax.barh(y_pos, pass_vals, label='Pass', color=(0.087, 0.639, 0.29), edgecolor='white')
        ax.barh(y_pos, fail_vals, left=pass_vals, label='Fail', color=(0.862, 0.149, 0.149), edgecolor='white')

        ax.set_yticks(y_pos)
        ax.set_yticklabels(services, fontsize=8)
        ax.set_xlabel('Count', fontsize=9)
        ax.legend(loc='lower right', fontsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        return _save_to_bytes(fig)
    except Exception as e:
        logger.error(f"Service chart error: {e}", exc_info=True)
        raise


def generate_pillar_chart(pillar_data: dict) -> io.BytesIO:
    """Vertical bar chart: findings by pillar."""
    try:
        if not pillar_data:
            pillar_data = {'No Data': 0}

        pillars = list(pillar_data.keys())
        counts = list(pillar_data.values())

        fig, ax = plt.subplots(figsize=(5.5, 3), facecolor='white')
        ax.set_facecolor((0.973, 0.98, 0.992))  # #F8FAFC in 0-1 RGB

        # Use 0-1 RGB blue color
        bars = ax.bar(pillars, counts, color=(0.231, 0.51, 0.961), width=0.5, edgecolor='white', linewidth=1)

        max_c = max(counts) if counts else 1
        for bar, val in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max_c * 0.02,
                   str(val), ha='center', va='bottom', fontsize=9, fontweight='bold',
                   color=(0.122, 0.227, 0.373))  # Dark blue in 0-1 RGB

        ax.set_ylabel('Count', fontsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_ylim(0, max_c * 1.15 if counts else 1)
        plt.xticks(rotation=15, ha='right', fontsize=8)
        plt.tight_layout()

        return _save_to_bytes(fig)
    except Exception as e:
        logger.error(f"Pillar chart error: {e}", exc_info=True)
        raise


def generate_risk_category_chart(risk_data: dict) -> io.BytesIO:
    """Horizontal bar chart: parameters by risk category."""
    try:
        categories = ['Critical', 'High', 'Medium', 'Low', 'Info']
        counts = [risk_data.get(cat.lower(), 0) for cat in categories]
        # Convert all colors to 0-1 RGB format
        cat_colors = [
            (0.862, 0.149, 0.149),      # Critical - Red
            (0.918, 0.345, 0.051),      # High - Orange
            (0.855, 0.463, 0.024),      # Medium - Yellow
            (0.396, 0.639, 0.051),      # Low - Green
            (0.149, 0.388, 0.933),      # Info - Blue
        ]

        fig, ax = plt.subplots(figsize=(5.5, 2.5), facecolor='white')
        ax.set_facecolor((0.973, 0.98, 0.992))  # #F8FAFC in 0-1 RGB

        bars = ax.barh(categories, counts, color=cat_colors, edgecolor='white', linewidth=1)

        max_c = max(counts) if counts else 1
        for bar, val in zip(bars, counts):
            ax.text(bar.get_width() + max_c * 0.02, bar.get_y() + bar.get_height()/2,
                   str(val), ha='left', va='center', fontsize=10, fontweight='bold',
                   color=(0.122, 0.227, 0.373))  # Dark blue in 0-1 RGB

        ax.set_xlabel('Number of Parameters', fontsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_xlim(0, max_c * 1.15 if counts else 1)

        return _save_to_bytes(fig)
    except Exception as e:
        logger.error(f"Risk category chart error: {e}", exc_info=True)
        raise

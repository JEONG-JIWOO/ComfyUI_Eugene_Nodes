// custom_widget.js
export function createComboToggleWidget(options = {}) {
  const {
    name = "preset-combo",
    values = [],
    defaultValue = "",
    isActive = false,
    onChange,
    onToggle
  } = options;

  return {
    type: "custom",
    name,
    values,
    value: defaultValue,
    isActive,

    draw(ctx, node, width, posY, height) {
      const margin = 5;
      const comboW = width * 0.75;
      const toggleW = width * 0.2;

      // 콤보박스 배경
      ctx.fillStyle = "#444";
      ctx.fillRect(margin, posY + margin, comboW - margin * 2, height - margin * 2);

      // 현재 선택값
      ctx.fillStyle = "#fff";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(this.value || "Select preset", margin + 8, posY + height * 0.65);

      // 토글 배경
      const toggleX = comboW + margin;
      ctx.fillStyle = this.isActive ? "#3b82f6" : "#333";
      ctx.fillRect(toggleX, posY + margin, toggleW - margin * 2, height - margin * 2);

      // 토글 체크마크
      if (this.isActive) {
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 2;
        ctx.beginPath();
        const x = toggleX + toggleW * 0.3;
        const y = posY + height * 0.5;
        ctx.moveTo(x, y);
        ctx.lineTo(x + 4, y + 4);
        ctx.lineTo(x + 8, y - 4);
        ctx.stroke();
      }
    },

    mouse(event, pos, node) {
      if (event.type !== "pointerdown") return false;

      const [x, y] = pos;
      const width = node.size[0];
      const comboW = width * 0.75;

      if (x >= 5 && x <= comboW - 5) {
        // 콤보박스 클릭
        const menu = new LiteGraph.ContextMenu(
          this.values,
          {
            event,
            callback: (value) => {
              this.value = value;
              if (onChange) onChange(value);
              node.graph.setDirtyCanvas(true);
            }
          },
          node.graph.canvas
        );
        return true;
      }
      else if (x >= comboW && x <= width - 5) {
        // 토글 클릭
        this.isActive = !this.isActive;
        if (onToggle) onToggle(this.isActive);
        node.graph.setDirtyCanvas(true);
        return true;
      }
      return false;
    }
  };
}

export function createHyperlinkWidget(options = {}) {
  const {
    name = "hyperlink",
    defaultUrl = "",
    onClick, // 클릭 시 추가 동작이 필요한 경우 사용할 콜백
  } = options;

  return {
    type: "custom",
    name,
    value: defaultUrl, // 링크 주소를 저장하는 필드
    draw(ctx, node, width, posY, height) {
      // 텍스트 스타일 설정 (링크 느낌의 파란색)
      ctx.fillStyle = "#3b82f6";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "center";

      // 표시할 텍스트: 값이 있다면 링크 주소, 없으면 "No Link"
      const displayText = this.value || "No Link";
      ctx.fillText(displayText, width / 2, posY + height / 2 + 4);
    },
    mouse(event, pos, node) {
      if (event.type !== "pointerdown") return false;

      // 가능한 모든 이벤트 전파 차단 메서드 호출
      if (event.stopImmediatePropagation) event.stopImmediatePropagation();
      if (event.stopPropagation) event.stopPropagation();
      if (event.preventDefault) event.preventDefault();

      // 클릭 시 링크 열기
      const url = this.value;
      if (url) {
        window.open(url, "_blank");
        if (onClick) onClick(url);
      }

      // **중요**: 클릭 후 mouse 핸들러를 제거하여 pointer.finally에서 호출되지 않도록 함.
      this.mouse = null;

      return true;
    }
  };
}

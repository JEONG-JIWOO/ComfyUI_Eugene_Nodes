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

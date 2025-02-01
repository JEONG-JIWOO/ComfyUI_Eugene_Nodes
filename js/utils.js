// 📌 파일: extensions/utils/utils.js
import { app } from "../../scripts/app.js";

/**
 * 📌 특정 위젯을 노드에서 찾는 헬퍼 함수
 * @param {object} node - PresetEditor 노드 객체
 * @param {string} widgetName - 찾을 위젯의 이름
 * @returns {object|null} - 찾은 위젯 객체 또는 null
 */
export function getWidget(node, widgetName) {
    const widget = node.widgets.find(w => w.name === widgetName);
    if (!widget) {
        console.warn(`[PresetEditor] Widget "${widgetName}" not found.`);
    }
    return widget || null;
}

/**
 * 📌 "Result" 위젯에 로그를 출력하는 함수
 * @param {object} node - PresetEditor 노드 객체
 * @param {string} type - 로그 타입 (`INFO`, `SUCCESS`, `ERROR`)
 * @param {string} message - 출력할 메시지
 */
export function customPrint(node, type, message) {
    const resultWidget = getWidget(node, "Result");
    if (resultWidget) {
        const timestamp = new Date().toLocaleTimeString();
        resultWidget.value = `[${type}] ${message} \n (${timestamp})\n`;
    }
}

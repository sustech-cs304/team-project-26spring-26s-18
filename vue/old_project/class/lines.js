//折线类,由3条线段组成,每条线段只能是水平或垂直的,第一条线段的起点是from_node的锚点坐标,最后一条线段的终点是to_node的锚点坐标,中间的线段连接两条线段,实际使用四个点来实现
export class Polyline {
  constructor(id, points, from_node = null, to_node = null, from_anchor = null, to_anchor = null) {
    this.id = id;
    this.points = points || [];
    this.from_node = from_node;
    this.to_node = to_node;
    this.from_anchor = from_anchor;
    this.to_anchor = to_anchor;
  }
  static createFromBackend(id, points, from_node, to_node, from_anchor, to_anchor) {
    return new Polyline(id, points, from_node, to_node, from_anchor, to_anchor);
  }

  // 序列化为后端可存储的对象
  toJSON() {
    return {
      id: this.id,
      points: this.points,
      from_node: this.from_node,
      to_node: this.to_node,
      from_anchor: this.from_anchor,
      to_anchor: this.to_anchor
    };
  }

  // 更新某个点坐标
  updatePoint(index, x, y) {
    if (index >= 0 && index < this.points.length) {
      this.points[index] = { x, y };
    }
  }
  // 获取起点坐标
  getStart() {
    return this.points[0];
  }
  // 获取终点坐标
  getEnd() {
    return this.points[this.points.length - 1];
  }
}
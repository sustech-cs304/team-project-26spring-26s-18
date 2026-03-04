export class Node {
  id;
  x;
  y;
  file_id;
  node_name;
  node_content;
  lines_from = []; //从该节点出发的线的id数组
  lines_to = [];   //到达该节点的线的id数组
  constructor(id, x, y, file_id, node_name, node_content, lines_from = [], lines_to = []) {
    this.id = id;
    this.x = x;
    this.y = y;
    this.file_id = file_id;
    this.node_name = node_name;
    this.node_content = node_content;
    this.lines_from = lines_from;
    this.lines_to = lines_to;
  }
  static createNewNode_back(id, x, y, file_id, node_name, node_content, lines_from, lines_to) {
    return new Node(id, x, y, file_id, node_name, node_content, lines_from, lines_to);
  }
}
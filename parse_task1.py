import xml.etree.ElementTree as ET
import sys

class PetriNet:
    def __init__(self):
        # Dữ liệu dạng Dictionary để truy cập nhanh theo ID
        self.places = {}      # { 'p1': { 'id': 'p1', 'token': 1 }, ... }
        self.transitions = {} # { 't1': { 'id': 't1', 'preset': [], 'postset': [] }, ... }
        self.arcs = []        # [ { 'source': 'p1', 'target': 't1' }, ... ]
        
        # Dữ liệu dạng List đã sắp xếp (quan trọng cho Ma trận và BDD)
        self.place_ids = []       # ['p1', 'p2', 'p3'...]
        self.transition_ids = []  # ['t1', 't2', 't3'...]
        
        # Ma trận liên thuộc (Incidence Matrix)
        self.incidence_matrix = [] 

    def load_from_pnml(self, file_path):
        """Đọc file PNML và xây dựng cấu trúc mạng"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except Exception as e:
            print(f"[LỖI] Không thể đọc file {file_path}: {e}")
            return False

        # 1. Xử lý Namespace (thường gặp trong PNML)
        try:
            ns_url = root.tag.split('}')[0].strip('{')
            ns = {'pnml': ns_url}
        except IndexError:
            ns = {} # Không có namespace
            
        # Helper để tìm tag có hoặc không có namespace
        def find_all(node, tag_name):
            if ns:
                return node.findall(f'.//pnml:{tag_name}', ns)
            return node.findall(f'.//{tag_name}')

        # 2. Parse Places
        for place in find_all(root, 'place'):
            p_id = place.get('id')
            initial_marking = 0
            
            # Lấy số token ban đầu (nếu có)
            marking_tag = None
            if ns:
                marking_tag = place.find('pnml:initialMarking', ns)
            else:
                marking_tag = place.find('initialMarking')
                
            if marking_tag is not None:
                # Tìm thẻ text bên trong initialMarking
                text_tag = marking_tag.find('pnml:text', ns) if ns else marking_tag.find('text')
                if text_tag is not None and text_tag.text:
                    initial_marking = int(text_tag.text)
            
            self.places[p_id] = {'id': p_id, 'token': initial_marking}

        # 3. Parse Transitions
        for trans in find_all(root, 'transition'):
            t_id = trans.get('id')
            self.transitions[t_id] = {
                'id': t_id, 
                'preset': [],   # Các place đầu vào
                'postset': []   # Các place đầu ra
            }

        # 4. Parse Arcs
        for arc in find_all(root, 'arc'):
            arc_id = arc.get('id')
            source = arc.get('source')
            target = arc.get('target')
            self.arcs.append({'id': arc_id, 'source': source, 'target': target})

        # 5. Xây dựng quan hệ luồng (Preset/Postset) và sắp xếp ID
        self._build_relationships()
        
        return True

    def _build_relationships(self):
        """Hàm nội bộ: Liên kết các node và tạo danh sách ID đã sắp xếp"""
        # Sắp xếp ID để đảm bảo thứ tự nhất quán cho Ma trận & BDD
        self.place_ids = sorted(self.places.keys())
        self.transition_ids = sorted(self.transitions.keys())

        # Reset preset/postset
        for t in self.transitions.values():
            t['preset'] = []
            t['postset'] = []

        # Điền preset/postset dựa trên arcs
        for arc in self.arcs:
            src, tgt = arc['source'], arc['target']
            
            # Nếu cung đi từ Place -> Transition (Input Arc)
            if src in self.places and tgt in self.transitions:
                self.transitions[tgt]['preset'].append(src)
            
            # Nếu cung đi từ Transition -> Place (Output Arc)
            elif src in self.transitions and tgt in self.places:
                self.transitions[src]['postset'].append(tgt)

        # Tạo ma trận liên thuộc ngay lập tức
        self._generate_incidence_matrix()

    def _generate_incidence_matrix(self):
        """
        Tạo Ma trận liên thuộc A [Size: |Places| x |Transitions|]
        A[p][t] = Weight(t, p) - Weight(p, t)
                = 1 (nếu t bắn ra p) - 1 (nếu t lấy từ p)
        """
        # Khởi tạo ma trận toàn số 0
        n_p = len(self.place_ids)
        n_t = len(self.transition_ids)
        
        # Matrix dạng list of lists: matrix[row_index][col_index]
        matrix = [[0] * n_t for _ in range(n_p)]

        for t_idx, t_id in enumerate(self.transition_ids):
            trans_data = self.transitions[t_id]
            
            # Trừ token ở Preset (Input)
            for p_id in trans_data['preset']:
                p_idx = self.place_ids.index(p_id)
                matrix[p_idx][t_idx] -= 1
            
            # Cộng token ở Postset (Output)
            for p_id in trans_data['postset']:
                p_idx = self.place_ids.index(p_id)
                matrix[p_idx][t_idx] += 1
                
        self.incidence_matrix = matrix

    def check_consistency(self):
        """Task 1.2: Kiểm tra tính nhất quán"""
        print("\n--- [CHECK] Kiểm tra tính nhất quán ---")
        all_nodes = set(self.places.keys()) | set(self.transitions.keys())
        errors = []

        if not self.places:
            errors.append("Mạng không có Place nào.")
        if not self.transitions:
            errors.append("Mạng không có Transition nào.")

        for arc in self.arcs:
            if arc['source'] not in all_nodes:
                errors.append(f"Arc {arc.get('id')} có source '{arc['source']}' không tồn tại.")
            if arc['target'] not in all_nodes:
                errors.append(f"Arc {arc.get('id')} có target '{arc['target']}' không tồn tại.")

        if not errors:
            print(">> PASSED: Mạng hợp lệ.")
            return True
        else:
            print(">> FAILED: Phát hiện lỗi:")
            for e in errors:
                print(f"   - {e}")
            return False

    def print_summary(self):
        """In tóm tắt thông tin mạng (Hỗ trợ viết báo cáo)"""
        print(f"\n=== PETRI NET SUMMARY ===")
        print(f"Số lượng Places: {len(self.places)}")
        print(f"Số lượng Transitions: {len(self.transitions)}")
        print(f"Số lượng Arcs: {len(self.arcs)}")
        
        print("\n--- Initial Marking (M0) ---")
        m0 = [self.places[p]['token'] for p in self.place_ids]
        print(f"M0 (Vector): {m0}")
        for p_id in self.place_ids:
            if self.places[p_id]['token'] > 0:
                print(f"  {p_id}: {self.places[p_id]['token']}")

        print("\n--- Incidence Matrix (A) ---")
        # In tiêu đề cột (Transitions)
        print(f"{'':>10} | " + "  ".join(f"{t:>4}" for t in self.transition_ids))
        print("-" * (10 + 6 * len(self.transition_ids)))
        
        # In từng dòng (Places)
        for i, row in enumerate(self.incidence_matrix):
            p_id = self.place_ids[i]
            row_str = "  ".join(f"{val:>4}" for val in row)
            print(f"{p_id:>10} | {row_str}")

# ==========================================
# VÍ DỤ SỬ DỤNG
# ==========================================
if __name__ == "__main__":
    # Thay tên file PNML của bạn vào đây
    pnml_file = "test_task5.pnml" 
    
    net = PetriNet()
    if net.load_from_pnml(pnml_file):
        if net.check_consistency():
            net.print_summary()
            
            # Dữ liệu để các bạn khác dùng:
            # Task 2 (BFS): dùng net.places, net.transitions
            # Task 4 (ILP): dùng net.incidence_matrix
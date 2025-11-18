import xml.etree.ElementTree as ET
import pprint

def parse_pnml(pnml_file):
    """
    Phần 1: Đọc file và Xây dựng Cấu trúc Dữ liệu
    """
    try:
        tree = ET.parse(pnml_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Lỗi: Không thể đọc file {pnml_file}. Lỗi: {e}")
        return None

    # Xử lý namespace 
    try:
        namespace_str = root.tag.split('}')[0].strip('{')
        namespaces = {'pnml': namespace_str}
    except IndexError:
        print("Lỗi: Không thể xác định namespace của file PNML.")
        return None

    places = {}
    transitions = {}
    arcs = []

    # Tìm tất cả places
    for place in root.findall('.//pnml:place', namespaces):
        place_id = place.get('id')
        initial_marking = 0
        marking_tag = place.find('pnml:initialMarking', namespaces)
        if marking_tag is not None:
            text_tag = marking_tag.find('pnml:text', namespaces)
            if text_tag is not None:
                initial_marking = int(text_tag.text)
        places[place_id] = {'initial_marking': initial_marking}

    # Tìm tất cả transitions
    for trans in root.findall('.//pnml:transition', namespaces):
        trans_id = trans.get('id')
        transitions[trans_id] = {'id': trans_id, 'preset': [], 'postset': []}

    # Tìm tất cả arcs
    for arc in root.findall('.//pnml:arc', namespaces):
        arc_id = arc.get('id')
        source_id = arc.get('source')
        target_id = arc.get('target')
        arcs.append({'id': arc_id, 'source': source_id, 'target': target_id})

    petri_net = {
        'places': places,
        'transitions': transitions,
        'arcs': arcs
    }
    
    # --- 2. Gán Preset/Postset cho Transitions ---
    all_nodes = places.keys() | transitions.keys()
    
    for arc in arcs:
        source = arc['source']
        target = arc['target']
        
        # Chỉ xử lý các arc hợp lệ (cả source và target đều tồn tại)
        if source in all_nodes and target in all_nodes:
            if source in places and target in transitions:
                transitions[target]['preset'].append(source)
            elif source in transitions and target in places:
                transitions[source]['postset'].append(target)
                
    return petri_net

def verify_consistency(petri_net):
    """
    Phần 2: Kiểm tra tính Nhất quán (Consistency Check)
    """
    print("\n--- Bắt đầu kiểm tra tính nhất quán ---")
    if not petri_net:
        print("Lỗi: Cấu trúc mạng rỗng.")
        return False

    places = petri_net['places']
    transitions = petri_net['transitions']
    arcs = petri_net['arcs']
    
    # Tạo một tập hợp (set) chứa ID của TẤT CẢ các node
    all_node_ids = set(places.keys()) | set(transitions.keys())
    
    all_valid = True
    
    for arc in arcs:
        source_id = arc['source']
        target_id = arc['target']
        
        # 1. Kiểm tra "missing nodes" (node bị thiếu)
        if source_id not in all_node_ids:
            print(f"[LỖI] Arc '{arc['id']}' có source '{source_id}' không tồn tại.")
            all_valid = False
            
        if target_id not in all_node_ids:
            print(f"[LỖI] Arc '{arc['id']}' có target '{target_id}' không tồn tại.")
            all_valid = False

    if all_valid:
        print("Tất cả các arc đều trỏ đến các node tồn tại.")
    else:
        print("Phát hiện lỗi. Vui lòng xem chi tiết ở trên.")

    return all_valid



if __name__ == "__main__":
    filename = 'test_task5.pnml'

    my_net = parse_pnml(filename)
    
    if my_net:
        print("\n--- 1. Cấu trúc dữ liệu bên trong (Internal Representation) ---")
        
        print("\nPlaces:")
        pprint.pprint(my_net['places'])
        
        print("\nTransitions (với preset/postset):")
        pprint.pprint(my_net['transitions'])
        
        print("\nArcs:")
        pprint.pprint(my_net['arcs'])
        verify_consistency(my_net)
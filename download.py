from __future__ import annotations
import json
import requests
import pathlib

VERBOSE = True
METADATA_FILE = 'metadata.json'

class Node:
    code: int
    name: str
    sub_nodes: dict[str, Node] # name -> node

    def __init__(self, code, name):
        self.code = code
        self.name = name
        self.sub_nodes = {}

    @staticmethod
    def from_json(j):
        n = Node(j['code'], j['name'])
        if j['sub_nodes']:
            n.sub_nodes = {k: Node.from_json(v) for k, v in j['sub_nodes'].items()}
        else:
            n.sub_nodes = {}
        return n

    def to_json(self):
        return {
            "code": int(self.code),
            "name": self.name,
            "sub_nodes": {
                k: v.to_json()
                for k, v in self.sub_nodes.items()
            }
        }
    

def init_skeleton(state_names_file) -> dict[str, Node]:
    with open(state_names_file, 'r') as f:
        contents: dict[str, str] = json.load(f)
    return {name: Node(code, name) for code, name in contents.items()}

def get_district_metadata(state_code) -> dict[str, Node]:
    if VERBOSE: print(f'Loading metadata for state: {state_code}')
    url = f'https://secc.gov.in/getDistrict.html?stateCode={state_code}'
    r = requests.get(url)
    j: list[dict[str, str]] = r.json()
    return {entry['district_name']: Node(entry['district_code'], entry['district_name']) for entry in j}

def get_block_metadata(state_code, district_code) -> dict[str, Node]:
    if VERBOSE: print(f'| Loading metadata for district: {district_code}')
    url = f'https://secc.gov.in/getDevlopmentBlockDetails.html?stateCode={state_code}&districtCode={district_code}'
    r = requests.get(url)
    j: list[dict[str, str]] = r.json()
    return {entry['block_name']: Node(entry['block_code'], entry['block_name']) for entry in j}

def get_gp_metadata(state_code, district_code, block_code) -> dict[str, Node]:
    if VERBOSE: print(f'  | Loading metadata for block: {block_code}')
    url = f'https://secc.gov.in/getLgdGrampanchayatDetail.html?stateCode={state_code}&districtCode={district_code}&blockCode={block_code}'
    r = requests.get(url)
    j: list[dict[str, str]] = r.json()
    return {entry['gp_name']: Node(entry['gp_code'], entry['gp_name']) for entry in j}

def save_metadata(metadata, filename):
    j = {name: node.to_json() for name, node in metadata.items()}
    json.dump(j, open(filename, 'w'))

def populate_metadata():
    # continue from existing save if one exists
    if pathlib.Path(METADATA_FILE).is_file():
        metadata_json = json.load(open(METADATA_FILE, 'r'))
        metadata = {k: Node.from_json(v) for k, v in metadata_json.items()}
    else:
        metadata = init_skeleton("state_names.json")

    try:
        for state_node in metadata.values():
            if not state_node.sub_nodes:
                state_node.sub_nodes = get_district_metadata(state_node.code)
            for district_node in state_node.sub_nodes.values():
                if not district_node.sub_nodes:
                    district_node.sub_nodes = get_block_metadata(state_node.code, district_node.code)
                for block_node in district_node.sub_nodes.values():
                    if not block_node.sub_nodes:
                        block_node.sub_nodes = get_gp_metadata(state_node.code, district_node.code, block_node.code)
        save_metadata(METADATA_FILE)
    except KeyboardInterrupt:
        print('Execution interrupted manually. Saving current state to metadata file.')
        save_metadata(METADATA_FILE)
    except Exception:
        filename = 'errored-' + METADATA_FILE
        print('Execution encountered error. Saving current state to ' + filename)
        save_metadata(filename)

    return metadata

def main():
    metadata = populate_metadata()
    print('loaded all metadata')

if __name__ == '__main__':
    main()
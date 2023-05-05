from __future__ import annotations
import json
import requests

VERBOSE = True

class Node:
    code: int
    name: str
    sub_nodes: dict[str, Node] # name -> node

    def __init__(self, code, name):
        self.code = code
        self.name = name
        self.sub_nodes = {}

    def to_json(self):
        return {
            "code": int(self.code),
            "name": self.name,
            "sub_nodes": {
                k: v.to_json()
                for k, v in self.sub_nodes.items()
            }
        }


def initialize_states(state_names_file) -> dict[str, Node]:
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

def populate_metadata(metadata: dict[str, Node]):
    try:
        for state_node in metadata.values():
            state_node.sub_nodes = get_district_metadata(state_node.code)
            for district_node in state_node.sub_nodes.values():
                district_node.sub_nodes = get_block_metadata(state_node.code, district_node.code)
                for block_node in district_node.sub_nodes.values():
                    block_node.sub_nodes = get_gp_metadata(state_node.code, district_node.code, block_node.code)
    except KeyboardInterrupt:
        print('Execution interrupted. Saving current state to metadata.json')
    finally:
        j = {name: node.to_json() for name, node in metadata.items()}
        json.dump(j, open('metadata.json', 'w'))

    return metadata

def main():
    metadata = initialize_states("state_names.json")
    populate_metadata(metadata)

if __name__ == '__main__':
    main()
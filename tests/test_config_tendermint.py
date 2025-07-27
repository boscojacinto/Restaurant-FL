import os
import subprocess

def main():
    cur_dir = os.getcwd()
    args = {}
    args['c_moniker'] = "restaurant1"
    args['c_persistent_peers'] = "04c6ff08d435e1b3f7fde44bdab924a166071bbb@192.168.1.26:26658"
    args['c_addr_book_strict'] = "false"
    args['c_allow_duplicate_ip'] = "true"
    args['c_wal_dir'] = "p2p/consensus"
    args['c_timeout_commit'] = "10s"
    args['c_create_empty_blocks'] = "false"
    args['c_index_tags'] = "order_tx_check,order_tx_deliver"

    try:
        result = subprocess.run(["sed", "-i", "-e", f's/moniker = "[^"]*"/moniker = "{args["c_moniker"]}"/',
            "-e", f's/persistent_peers = "[^"]*"/persistent_peers = "{args["c_persistent_peers"]}"/',
            "-e", rf's/addr_book_strict = \(true\|false\)/addr_book_strict = {args["c_addr_book_strict"]}/',
            "-e", rf's/allow_duplicate_ip = \(true\|false\)/allow_duplicate_ip = {args["c_allow_duplicate_ip"]}/',
            "-e", f's/wal_dir = "[^"]*"/wal_dir = "{args["c_wal_dir"].replace('/', r'\/')}"/',
            "-e", f's/timeout_commit = "[^"]*"/timeout_commit = "{args["c_timeout_commit"]}"/',
            "-e", rf's/create_empty_blocks = \(true\|false\)/create_empty_blocks = {args["c_create_empty_blocks"]}/',
            f"{env['TMHOME']}/config/config.toml"],
        cwd=cur_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error configuring tendermint:{e}")
        return 1

    try:
        result = subprocess.run(["sed", "-n", 
            f'/index_tags = "[^"]*"/p',
            f"{env['TMHOME']}/config/config.toml"],
        cwd=cur_dir, check=True, capture_output=True, text=True)

        if not result.stdout:
            try:
                result = subprocess.run(["sed", "-i", 
                    "-e", rf's/indexer = \("null"\|"kv"\|"psql"\)/indexer = "kv"\nindex_tags = "{args["c_index_tags"]}"/',
                    f"{env['TMHOME']}/config/config.toml"],
                cwd=cur_dir, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                print(f"Error configuring tendermint:{e}")
                return 1
    except subprocess.CalledProcessError as e:
        print(f"Error configuring tendermint:{e}")
        return 1

if __name__ == '__main__':
    main()
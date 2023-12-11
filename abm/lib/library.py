from pprint import pprint

from .common import Context, connect, datasets


def list(context: Context, args: list):
    gi = connect(context)
    if len(args) == 0:
        for library in gi.libraries.get_libraries():
            print(f"{library['id']}\t{library['name']}\t{library['description']}")
        return
    folders = gi.libraries.show_library(args[0], contents=True)
    for folder in folders:
        print(f"{folder['id']}\t{folder['type']}\t{folder['name']}")


def create(context: Context, args: list):
    if len(args) != 2:
        print("ERROR: Invalid parameters, at least the name must be specified")
        return
    name = args[0]
    description = None
    if len(args) == 2:
        description = args[1]
    gi = connect(context)
    result = gi.libraries.create_library(name, description=description)
    pprint(result)


def delete(context: Context, args: list):
    print("library delete not implemented")


def upload(context: Context, args: list):
    if len(args) != 3:
        print(
            "ERROR: Invalid parameters. Specify the library and folder names and the dataset to upload"
        )
        return
    gi = connect(context)
    libraries = gi.libraries.get_libraries(name=args[0])
    if len(libraries) == 0:
        print(f"ERROR: No such library found: {args[0]}")
        return
    if len(libraries) > 1:
        print(f"WARNING: more than one library name matched. Using the first one found")
        for library in libraries:
            print(f"{library['id']}\t{library['create_time']}\t{library['name']}")

    library_id = libraries[0]['id']
    folders = gi.libraries.get_folders(library_id, name=args[1])
    if len(folders) == 0:
        print(f"ERROR: no folder with the name: {args[1]}")
        return
    folder_id = folders[0]['id']
    dataset_url = datasets['dna'][int(args[2])]
    result = gi.libraries.upload_file_from_url(
        library_id, dataset_url, folder_id=folder_id
    )
    pprint(result)
    return

    # library_id = args[0]
    # if len(args) == 3:
    #     folder_id = args[1]
    #     file_url = datasets['dna'][int(args[2])]
    # else:
    #     file_url = datasets['dna'][int(args[1])]
    # # ftp://ftp.sra.ebi.ac.uk/vol1/fastq/SRR592/SRR592109/SRR592109_2.fastq.gz
    # result = gi.libraries.upload_file_from_url(library_id, file_url, folder_id=folder_id)
    # pprint(result)


def download(context: Context, args: list):
    print("library download not implemented")


def show(context: Context, args: list):
    print("library show not implemented")

import argparse


def greet(name: str = "World") -> str:
    if not isinstance(name, str):
        raise TypeError("name must be a string")

    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("name must not be empty")

    return f"Hello, {normalized_name}!"


def main() -> None:
    parser = argparse.ArgumentParser(description="A small Jenkins CI demo app")
    parser.add_argument("--name", default="World", help="name to greet")
    arguments = parser.parse_args()
    print(greet(arguments.name))


if __name__ == "__main__":
    main()

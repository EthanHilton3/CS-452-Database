"""Check-digit math for UPC-A (12), EAN-13 (13), EAN-8 (8), UPC-E (8, starts 0/1) and GTIN-14."""


def _mod10(body: str) -> int:
    """Check digit for the digits before it: weights 3,1,3,1... counted from the right of the body."""
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10


def upce_to_upca(u: str) -> str:
    """Expand an 8-digit UPC-E (number system + 6 digits + check) to the 12-digit UPC-A it stands for."""
    ns, d, chk = u[0], u[1:7], u[7]
    last = d[5]
    if last in '012':
        body = d[0:2] + last + '0000' + d[2:5]
    elif last == '3':
        body = d[0:3] + '00000' + d[3:5]
    elif last == '4':
        body = d[0:4] + '00000' + d[4]
    else:
        body = d[0:5] + '0000' + last
    return ns + body + chk


def kind(digits: str) -> str | None:
    n = len(digits)
    if not digits.isdigit():
        return None
    if n == 12:
        return 'UPC-A'
    if n == 13:
        return 'ISBN-13' if digits[:3] in ('978', '979') else 'EAN-13'
    if n == 8:
        return 'UPC-E' if digits[0] in '01' else 'EAN-8'
    if n == 14:
        return 'GTIN-14'
    return None


def checksum_valid(digits: str) -> bool:
    k = kind(digits)
    if k is None:
        return False
    if k == 'UPC-E':  # UPC-E is only valid if its UPC-A expansion is; EAN-8 math does not apply
        a = upce_to_upca(digits)
        return _mod10(a[:-1]) == int(a[-1])
    return _mod10(digits[:-1]) == int(digits[-1])


def to_gtin13(digits: str) -> str:
    """Canonical key for lookups and the cache: UPC-E expands to UPC-A, then everything pads to 13 digits."""
    if kind(digits) == 'UPC-E':
        digits = upce_to_upca(digits)
    return digits.zfill(13) if len(digits) < 14 else digits


if __name__ == '__main__':  # quick self-test with known-good codes
    assert checksum_valid('036000291452') and checksum_valid('4006381333931') and checksum_valid('96385074')
    assert checksum_valid('9780306406157') and not checksum_valid('036000291453')
    assert checksum_valid('01234565') and kind('01234565') == 'UPC-E'  # expands to 012345000065
    print('ok')

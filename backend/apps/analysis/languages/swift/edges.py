import re

_IMPORT_RE = re.compile(r'^\s*import\s+([\w.]+)', re.MULTILINE)

_STDLIB = frozenset({
    'Swift', 'Foundation', 'UIKit', 'AppKit', 'SwiftUI', 'Combine', 'CoreData',
    'CoreFoundation', 'CoreGraphics', 'CoreLocation', 'CoreMotion', 'CoreNFC',
    'CoreText', 'CoreVideo', 'ARKit', 'AVFoundation', 'CFNetwork', 'CloudKit',
    'Contacts', 'CoreBluetooth', 'CoreImage', 'CryptoKit', 'EventKit',
    'GameKit', 'HealthKit', 'HomeKit', 'MapKit', 'MessageUI', 'Metal',
    'ModelIO', 'MultipeerConnectivity', 'NaturalLanguage', 'Network',
    'NotificationCenter', 'Photos', 'RealityKit', 'SafariServices',
    'SceneKit', 'SpriteKit', 'StoreKit', 'UserNotifications',
    'Vision', 'WatchKit', 'WebKit', 'XCTest', 'Darwin', 'Dispatch',
    'ObjectiveC', 'os', 'simd',
})


def _is_external(dep: str) -> bool:
    return dep in _STDLIB


def extract_edges(fpath: str, content: str, repo_dir: str) -> list[str]:
    return [m.group(1) for m in _IMPORT_RE.finditer(content)
            if m.group(1) and not _is_external(m.group(1))]

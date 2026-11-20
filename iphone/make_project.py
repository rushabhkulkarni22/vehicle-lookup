"""Generate the checked-in Xcode project using only Python's standard library."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
objects = {}
counter = 0

def obj(isa, **values):
    global counter
    counter += 1
    key = f'{counter:024X}'
    objects[key] = {'isa': isa, **values}
    return key

def configs(settings):
    values = []
    for name in ['Debug', 'Release']:
        config = dict(settings)
        if name == 'Debug':
            config.update(SWIFT_OPTIMIZATION_LEVEL='-Onone', SWIFT_ACTIVE_COMPILATION_CONDITIONS='DEBUG $(inherited)')
        values.append(obj('XCBuildConfiguration', name=name, buildSettings=config))
    return obj('XCConfigurationList', buildConfigurations=values, defaultConfigurationIsVisible='0', defaultConfigurationName='Release')

def ref(path, kind):
    return obj('PBXFileReference', path=path, lastKnownFileType=kind, sourceTree='<group>')

app_files = [ref('FindVehicleApp.swift', 'sourcecode.swift'), ref('Vehicle.swift', 'sourcecode.swift')]
test_file = ref('VehicleParserTests.swift', 'sourcecode.swift')
asset_ref = ref('Assets.xcassets', 'folder.assetcatalog')
app_group = obj('PBXGroup', children=app_files + [asset_ref], path='FindVehicle', sourceTree='<group>')
test_group = obj('PBXGroup', children=[test_file], path='FindVehicleTests', sourceTree='<group>')
app_product = obj('PBXFileReference', explicitFileType='wrapper.application', path='FindVehicle.app', sourceTree='BUILT_PRODUCTS_DIR', includeInIndex='0')
test_product = obj('PBXFileReference', explicitFileType='wrapper.cfbundle', path='FindVehicleTests.xctest', sourceTree='BUILT_PRODUCTS_DIR', includeInIndex='0')
products = obj('PBXGroup', children=[app_product, test_product], name='Products', sourceTree='<group>')
main_group = obj('PBXGroup', children=[app_group, test_group, products], sourceTree='<group>')
package = obj('XCRemoteSwiftPackageReference', repositoryURL='https://github.com/scinfu/SwiftSoup.git', requirement={'kind': 'exactVersion', 'version': '2.6.0'})
package_product = obj('XCSwiftPackageProductDependency', package=package, productName='SwiftSoup')

def phase(kind, files):
    return obj(kind, buildActionMask='2147483647', files=files, runOnlyForDeploymentPostprocessing='0')

sources = phase('PBXSourcesBuildPhase', [obj('PBXBuildFile', fileRef=f) for f in app_files])
frameworks = phase('PBXFrameworksBuildPhase', [obj('PBXBuildFile', productRef=package_product)])
resources = phase('PBXResourcesBuildPhase', [obj('PBXBuildFile', fileRef=asset_ref)])
settings = dict(SWIFT_VERSION='5.0', IPHONEOS_DEPLOYMENT_TARGET='16.0', SDKROOT='iphoneos',
                TARGETED_DEVICE_FAMILY='1', CODE_SIGN_STYLE='Automatic', GENERATE_INFOPLIST_FILE='YES',
                CURRENT_PROJECT_VERSION='1', MARKETING_VERSION='1.0', PRODUCT_NAME='$(TARGET_NAME)',
                SUPPORTED_PLATFORMS='iphoneos iphonesimulator', SUPPORTS_MACCATALYST='NO')
app_settings = dict(settings, PRODUCT_BUNDLE_IDENTIFIER='com.rushabhkulkarni.findvehicle',
                    INFOPLIST_KEY_CFBundleDisplayName='Find Vehicle',
                    INFOPLIST_KEY_UILaunchScreen_Generation='YES',
                    INFOPLIST_KEY_UIApplicationSceneManifest_Generation='YES',
                    INFOPLIST_KEY_UISupportedInterfaceOrientations='UIInterfaceOrientationPortrait UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight',
                    ASSETCATALOG_COMPILER_APPICON_NAME='AppIcon',
                    LD_RUNPATH_SEARCH_PATHS='$(inherited) @executable_path/Frameworks')
app_target = obj('PBXNativeTarget', name='FindVehicle', productName='FindVehicle', productType='com.apple.product-type.application',
                 productReference=app_product, buildConfigurationList=configs(app_settings), buildPhases=[sources, frameworks, resources],
                 buildRules=[], dependencies=[], packageProductDependencies=[package_product])
test_settings = dict(settings, PRODUCT_BUNDLE_IDENTIFIER='com.rushabhkulkarni.findvehicle.tests',
                     TEST_HOST='$(BUILT_PRODUCTS_DIR)/FindVehicle.app/$(BUNDLE_EXECUTABLE_FOLDER_PATH)/FindVehicle',
                     BUNDLE_LOADER='$(TEST_HOST)', LD_RUNPATH_SEARCH_PATHS='$(inherited) @executable_path/Frameworks @loader_path/Frameworks')
test_target = obj('PBXNativeTarget', name='FindVehicleTests', productName='FindVehicleTests', productType='com.apple.product-type.bundle.unit-test',
                  productReference=test_product, buildConfigurationList=configs(test_settings),
                  buildPhases=[phase('PBXSourcesBuildPhase', [obj('PBXBuildFile', fileRef=test_file)]), phase('PBXFrameworksBuildPhase', [])],
                  buildRules=[], dependencies=[])
project = obj('PBXProject', attributes={'LastUpgradeCheck': '1600', 'TargetAttributes': {app_target: {'CreatedOnToolsVersion': '16.0'}, test_target: {'TestTargetID': app_target}}},
              buildConfigurationList=configs({'CLANG_ENABLE_MODULES': 'YES', 'ENABLE_TESTABILITY': 'YES', 'SWIFT_VERSION': '5.0', 'IPHONEOS_DEPLOYMENT_TARGET': '16.0'}),
              compatibilityVersion='Xcode 14.0', developmentRegion='en', hasScannedForEncodings='0', knownRegions=['en', 'Base'],
              mainGroup=main_group, productRefGroup=products, projectDirPath='', projectRoot='', targets=[app_target, test_target], packageReferences=[package])
proxy = obj('PBXContainerItemProxy', containerPortal=project, proxyType='1', remoteGlobalIDString=app_target, remoteInfo='FindVehicle')
dependency = obj('PBXTargetDependency', target=app_target, targetProxy=proxy)
objects[test_target]['dependencies'] = [dependency]

def serialize(value, depth=0):
    indent = '\t' * depth
    if isinstance(value, dict):
        return '{\n' + ''.join('\t' * (depth+1) + json.dumps(k) + ' = ' + serialize(v, depth+1) + ';\n' for k, v in value.items()) + indent + '}'
    if isinstance(value, list):
        return '(' + ', '.join(serialize(v, depth) for v in value) + (',' if value else '') + ')'
    return json.dumps(value)

project_dir = root / 'FindVehicle.xcodeproj'
project_dir.mkdir(exist_ok=True)
(project_dir / 'project.pbxproj').write_text('// !$*UTF8*$!\n' + serialize({'archiveVersion': '1', 'classes': {}, 'objectVersion': '56', 'objects': objects, 'rootObject': project}) + '\n', encoding='utf-8')
scheme_dir = project_dir / 'xcshareddata' / 'xcschemes'
scheme_dir.mkdir(parents=True, exist_ok=True)
def reference(target, name):
    return f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{target}" BuildableName="{name}" BlueprintName="{name.split(".")[0]}" ReferencedContainer="container:FindVehicle.xcodeproj"/>'
app_reference = reference(app_target, 'FindVehicle.app')
test_reference = reference(test_target, 'FindVehicleTests.xctest')
(scheme_dir / 'FindVehicle.xcscheme').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="1600" version="1.3">
 <BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries>
  <BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" buildForArchiving="YES" buildForAnalyzing="YES">{app_reference}</BuildActionEntry>
 </BuildActionEntries></BuildAction>
 <TestAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" shouldUseLaunchSchemeArgsEnv="YES"><Testables><TestableReference skipped="NO">{test_reference}</TestableReference></Testables></TestAction>
 <LaunchAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" launchStyle="0" useCustomWorkingDirectory="NO" ignoresPersistentStateOnLaunch="NO" debugDocumentVersioning="YES" debugServiceExtension="internal" allowLocationSimulation="YES"><BuildableProductRunnable runnableDebuggingMode="0">{app_reference}</BuildableProductRunnable></LaunchAction>
 <ProfileAction buildConfiguration="Release" shouldUseLaunchSchemeArgsEnv="YES" savedToolIdentifier="" useCustomWorkingDirectory="NO" debugDocumentVersioning="YES"><BuildableProductRunnable runnableDebuggingMode="0">{app_reference}</BuildableProductRunnable></ProfileAction>
 <AnalyzeAction buildConfiguration="Debug"/>
 <ArchiveAction buildConfiguration="Release" revealArchiveInOrganizer="YES"/>
</Scheme>
''', encoding='utf-8')
print('Generated FindVehicle.xcodeproj')
